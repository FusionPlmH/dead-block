#!/bin/bash
INPUT_FILE="splitblock07"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock7
    fi
done < "$INPUT_FILE"