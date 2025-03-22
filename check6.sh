#!/bin/bash
INPUT_FILE="splitblock06"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock6
    fi
done < "$INPUT_FILE"