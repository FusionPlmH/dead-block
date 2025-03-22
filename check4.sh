#!/bin/bash
INPUT_FILE="splitblock04"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock4
    fi
done < "$INPUT_FILE"