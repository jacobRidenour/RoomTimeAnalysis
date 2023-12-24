import os
import pandas as pd
import numpy as np
import shutil
import argparse

# ss.ff -> ss.ms
def prachack_to_dec(time):
    if pd.isna(time):
        return np.nan
    time = f'{time:.2f}'
    seconds, frames = map(int, time.split('.'))
    return seconds + frames / 60.0


# ss.ms -> ss.ff
def dec_to_prachack(time):
    if pd.isna(time):
        return np.nan
    seconds = int(time)
    frames = int((time - seconds)*60)
    return f'{seconds}.{frames:02d}'


# split input csvs into parts based on resets
# TODO: do it all in place instead of creating files?
def preprocess_csv_files(directory):
    preproc_dir = os.path.join(directory, 'csv_preproc')
    os.makedirs(preproc_dir, exist_ok=True)

    for filename in os.listdir(directory):
        if filename.endswith('.csv'):
            filepath = os.path.join(directory, filename)
            df = pd.read_csv(filepath, header=None, names=['RoomID', 'RoomName', 'PracticeRomTime', 'IGT', 'RTA', 'LagFrames'])

            # reset detection - Ceres Elevator Room should be preceded by Falling Tile Room, and Landing Site should follow it, otherwise -> it's a reset
            NotFallingTile = df['RoomName'].shift(1) != "Falling Tile Room"
            isCeresElevator = df['RoomName'] == "Ceres Elevator Room"
            NotLandingSite = df['RoomName'].shift(-1) != "Landing Site"
            resetCondition = isCeresElevator & (NotFallingTile | NotLandingSite)

            # indices where new CSV should start
            splitIndices = df.index[resetCondition].tolist()

            if splitIndices:
                splitIndices = [0] + splitIndices + [len(df)]

            # no resets found -> process the entire file as one segment
            if not splitIndices:
                splitIndices = [0, len(df)]

            for i in range(len(splitIndices) - 1):
                startIndex = splitIndices[i]
                stopIndex = splitIndices[i + 1]
                dfSplit = df.iloc[startIndex:stopIndex]
                splitFilename = f"{filename.rstrip('.csv')}_part{i + 1}.csv"
                dfSplit.to_csv(os.path.join(preproc_dir, splitFilename), index=False, header=True)


# turn everything into One Big Dataframe(TM)
def concatenate_runs(directory):
    allRuns = []
    runNumber = 1

    for filename in os.listdir(directory):
        if filename.endswith('.csv'):
            filepath = os.path.join(directory, filename)
            df = pd.read_csv(filepath)
            if not df.empty:
                # add rowIndex column - order of rooms - also ez way to find out how many rooms are in a category
                df['Run'] = runNumber
                df['RowIndex'] = df.index
                allRuns.append(df)
                runNumber += 1

    df_allRuns = pd.concat(allRuns, ignore_index=True)

    rowsList = []
    
    for index, group in df_allRuns.groupby('RowIndex'):
        # get the room ID and name from the first run
        roomID = group.iloc[0]['RoomID']
        roomName = group.iloc[0]['RoomName']

        rowData = {'RowIndex': index, 'RoomID': roomID, 'RoomName': roomName}

        # for each run: add data / blank entries
        for run in range(1, runNumber):
            runData = group[group['Run'] == run]
            if not runData.empty:
                for col in ['PracticeRomTime', 'IGT', 'RTA', 'LagFrames']:
                    rowData[f'{col}_Run{run}'] = runData.iloc[0][col]
            else:
                for col in ['PracticeRomTime', 'IGT', 'RTA', 'LagFrames']:
                    rowData[f'{col}_Run{run}'] = None

        rowsList.append(rowData)

    # turn into One Big Dataframe
    merged_df = pd.DataFrame(rowsList)
    return merged_df


# calculate best time, avg time, stdev (RTA columns only)
def calc_stats(df, RTA=True):
    rowsList = []

    colNameToUse = 'RTA_Run' if RTA else 'PracticeRomTime_Run'

    numRuns = max([int(col.split('_')[-1][3:]) for col in df.columns if col.startswith(colNameToUse)])

    # for each row, iterate & calculate stats
    for index, row in df.iterrows():
        values = [row[f'{colNameToUse}{i}'] for i in range(1, numRuns + 1) if pd.notna(row[f'{colNameToUse}{i}'])]

        if not RTA:
            values = [prachack_to_dec(val) for val in values]

        bestTime = min(values) if values else np.nan
        avgTime = np.mean(values) if values else np.nan
        stdevTime = np.std(values, ddof=0) if len(values) > 1 else 0
        n = len(values)

        if not RTA:
            bestTime = dec_to_prachack(bestTime)
            avgTime = dec_to_prachack(avgTime)
            stdevTime = dec_to_prachack(stdevTime)

        row_data = {
            'RowIndex': row['RowIndex'], 
            'RoomID': row['RoomID'], 
            'RoomName': row['RoomName'], 
            'N': n,
            'BestTime': bestTime, 
            'AverageTime': avgTime, 
            'StdDevTime': stdevTime
        }
        rowsList.append(row_data)

    results_df = pd.DataFrame(rowsList)
    return results_df

parser = None
def main():
    # Set up argparse to handle command-line arguments
    parser = argparse.ArgumentParser(description='Process room times for a single Super Metroid route/category from CSVs generated by FUNtoon.',
                                     usage='%(prog)s --CSVdir <directory> --Output <filename> [--RTA]',
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--CSVdir', required=True, type=str, help='Full path to a directory containing only CSV files with room times.')
    parser.add_argument('--RTA', action='store_true', help='Set this flag to use real time formatting (ss.ms).')
    parser.add_argument('--Output', required=True, type=str, help='Name for the output file.')

    args = parser.parse_args()

    directory = args.CSVdir
    outFile = args.Output
    if not outFile.endswith('.csv'):
        outFile += '.csv'
    
    # default = true = practice hack format; false = RTA
    outputType = not args.RTA

    print(f'Output will use {"practice hack time formatting (ss.ff)" if outputType else "real time formatting (ss.ms)"}.')

    preprocess_csv_files(directory)
    concatenated_stats = concatenate_runs(os.path.join(directory, 'csv_preproc'))
    calculated_stats = calc_stats(concatenated_stats, outputType)

    outputPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), outFile)
    calculated_stats.to_csv(outputPath, index=False)
    print(f'Output saved to {outputPath}')


if __name__ == '__main__':
    try:
        main()
    except argparse.ArgumentError as e:
        print(f'Error: {e}')
        parser.print_help()