Thanks to Taw, [FUNtoon](https://funtoon.party/) can now export CSV files containing room times for people speedrunning Super Metroid.

This script will take those files, parse them, and provide a summary of statistics for various rooms, including Best Time, Average Time, and Standard Deviation, as well as the sample size for each room. Currently, the results are always saved to the same directory as the script.

The input directory (`--CSVdir`) should be one that only contains room time .csvs output by FUNtoon for a single speedrun category.

Here's an example of how you use it in Command Prompt/PowerShell:

`python RoomTimeAnalysis.py --CSVdir C:\path\to\csv\folder --Output results.csv --RTA`

And here's how you'd use it in Bash/Zsh or similar shells:

`python RoomTimeAnalysis.py --CSVdir /c/path/to/csv/folder --Output results.csv --RTA`

If you do not include the --RTA flag, the output will be in practice hack format (seconds.frames) rather than (seconds.milliseconds).
