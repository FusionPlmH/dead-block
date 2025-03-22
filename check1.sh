#!/bin/bash
INPUT_FILE="splitblock01"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock1
    fi
done < "$INPUT_FILE"