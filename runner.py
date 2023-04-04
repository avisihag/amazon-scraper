import subprocess

if __name__ == '__main__':
    # Load the list of URLs from the file
    with open("search_results_output.txt", 'r') as urllist:
        urls = urllist.read().splitlines()

    # Divide the URLs into 25 groups
    num_groups = 25
    buffer = 43193
    urls = urls[buffer:]
    group_size = (len(urls) + num_groups - 1) // num_groups
    # group_size = 2
    groupings = [(k+buffer, k+group_size+buffer) for k in range(0, len(urls), group_size)]
    url_groups = [urls[i:i+group_size] for i in range(0, len(urls), group_size)]

    # Process each group of URLs in a separate terminal
    for i, group in enumerate(url_groups):
        # Create a separate output file for each group
        output_filename = f"output{i+1}.jsonl"
        empty_filename = f"emptyfile{i+1}.jsonl"

        # Run the script for this group of URLs in a separate terminal
        command = f"python3 scrape.py -c beauty --urls_file {urllist.name} --output_file {output_filename} --empty_file {empty_filename} --start {groupings[i][0]} --end {groupings[i][1]}"
        # print(command)
        subprocess.Popen(command, shell=True)
