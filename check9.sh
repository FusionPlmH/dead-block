#!/bin/bash
INPUT_FILE="splitblock09"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock9
    fi
done < "$INPUT_FILE"