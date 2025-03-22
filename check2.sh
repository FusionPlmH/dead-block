#!/bin/bash
INPUT_FILE="splitblock02"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock2
    fi
done < "$INPUT_FILE"