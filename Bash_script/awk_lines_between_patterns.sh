#!/usr/bin/bash
# v.0.1 : Get a directory path for text files that have Citrix ADC terminal logs and find the result of a Certain command
# Input : text files path
# Sample : ./awk_lines_between_patterns.v.1.1.sh /running/config/directory/path/

if [ $# -ge 2 ]; then
    echo "Let's do this one at a time, dude"
    exit 0
fi
path="$1"
echo "Input file : "$path
if [ ! -d ${path} ]; then  ## https://stackoverflow.com/questions/638975/how-do-i-tell-if-a-file-does-not-exist-in-bash
    echo "That file ${path} doesn't exist. Check again"
    exit 0
fi
echo "The input file path exists.. Processing.."
echo ""

#pattern1="ns\.log[\.[:alnum:]]*[[:space:]]*$" ## REGEX for sed & awk
pattern1="show run"
pattern2="Done"
prompt_pattern="MPX[0-9a-zA-Z\-\.]*_(Primary|Secondary)> "
#prompt_pattern="root@[0-9a-zA-Z\-]*#"
pattern1_line="${prompt_pattern}${pattern1}"
outfile=".conf"

rm "$outfile"
for filename in "$path"/*.log
do
    echo "grep -P ${pattern1_line} ${filename}"
    echo ""
    prompt_line="$(grep -P "${pattern1_line}" "${filename}")"
    echo "Prompt Line : "$prompt_line
    if [ -z "$prompt_line" ]; then
        echo "No matching line found."
        exit 1
    fi
    echo "Start Pattern : "$pattern1
    echo "Ending Pattern : "$pattern2
    echo ""
    awk -v start="$pattern1" -v end="$pattern2" '{
        if ($0 ~ start) {print; flag=1; next}
        if (flag) {print}
        if ($0 ~ end) {flag=0}
    }' "$filename" >> "${filename}${outfile}"

    ## 
    echo "The result will be in ${filename}${outfile}"
    sleep 0.1
done

echo "Done!"
exit 0
