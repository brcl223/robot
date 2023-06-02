import os

def find_run_num(datadir):
    max_seen = 0
    for filename in os.scandir(datadir):
        if filename.is_file and ".run-" in filename.name:
            run_str_start = filename.name.find('.run-') + len('.run-')
            # print(f"rss: {run_str_start}")
            # print(f"Fname len: {len(filename.name)}")
            # print(f"Filename: {filename.name}")
            # print(f"Selected substring: {filename.name[run_str_start:run_str_start+3]}")
            max_seen = max(max_seen, int(filename.name[run_str_start:run_str_start+3]))
    return max_seen
