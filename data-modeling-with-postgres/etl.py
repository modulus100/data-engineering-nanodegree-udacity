import os
import glob
import psycopg2
import psycopg2.extras
import pandas as pd
from sql_queries import *


def process_song_file(cur, filepath):
    """
    Reads raw data from the data files to split artist and songs
    corresponding tables
    :param cur: Postgres cursor
    :param filepath: A path to a file to process
    :return: void
    """
    # open song file
    df = pd.read_json(filepath, lines=True)

    # ideally should be added in batch, iterative approach is just for simplicity
    # not sure if it's a good option to store data in array, just testing batch insert
    songs = []
    artists = []

    for index, row in df.iterrows():
        songs.append((row.song_id, row.title, row.artist_id, row.year, row.duration))
        artists.append((row.artist_id, row.artist_name, row.artist_location,
                       row.artist_latitude, row.artist_longitude))

    psycopg2.extras.execute_batch(cur, song_table_insert, songs)
    psycopg2.extras.execute_batch(cur, artist_table_insert, artists)


def process_log_file(cur, filepath):
    """
    This function is responsible for splitting raw log data and saving it
    in different postgres tables
    :param cur: Postgres cursor
    :param filepath: A path to a file to process
    :return: void
    """
    # open log file
    df = pd.read_json(filepath, lines=True)

    # filter by NextSong action
    df = df[df.page == 'NextSong']

    # convert timestamp column to datetime
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    t = df.copy()

    # insert time data records
    time_data = (t.ts, t.ts.dt.hour, t.ts.dt.day, t.ts.dt.dayofweek,
                 t.ts.dt.month, t.ts.dt.year, t.ts.dt.weekday)
    column_labels = ['start_time', 'hour', 'day', 'week',
                     'month', 'year', 'weekday']
    time_df = pd.DataFrame(columns=column_labels)

    for index, column_label in enumerate(column_labels):
        time_df[column_label] = time_data[index]

    for _, row in time_df.iterrows():
        cur.execute(time_table_insert, list(row))

        # load user table
    user_df = df[['userId', 'firstName', 'lastName', 'gender', 'level']]

    # insert user records
    for i, row in user_df.iterrows():
        cur.execute(user_table_insert, row)

    # insert songplay records
    for index, row in df.iterrows():

        # get songid and artistid from song and artist tables
        cur.execute(song_select, (row.song, row.artist, row.length))
        results = cur.fetchone()

        if results:
            songid, artistid = results
        else:
            songid, artistid = None, None

        # insert songplay record
        songplay_data = (row.ts, row.userId, row.level, songid, artistid,
                         row.sessionId, row.location, row.userAgent)
        cur.execute(songplay_table_insert, songplay_data)


def process_data(cur, conn, filepath, func):
    """
    Handles the rat data files and inserts the data into postgres

    :param cur: Postgres cursor
    :param conn: Postgres connection
    :param filepath: A path to a file to process
    :param func: function handler is responsible for the data insertion
    :return: void
    """
    # get all files matching extension from directory
    all_files = []
    for root, dirs, files in os.walk(filepath):
        files = glob.glob(os.path.join(root, '*.json'))
        for f in files:
            all_files.append(os.path.abspath(f))

    # get total number of files found
    num_files = len(all_files)
    print('{} files found in {}'.format(num_files, filepath))

    # iterate over files and process
    for i, datafile in enumerate(all_files, 1):
        func(cur, datafile)
        conn.commit()
        print('{}/{} files processed.'.format(i, num_files))


def main():
    conn = psycopg2.connect("host=127.0.0.1 dbname=sparkifydb user=student password=student")
    cur = conn.cursor()

    try:
        process_data(cur, conn, filepath='data/song_data', func=process_song_file)
        process_data(cur, conn, filepath='data/log_data', func=process_log_file)
    except psycopg2.Error as e:
        print(e)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
