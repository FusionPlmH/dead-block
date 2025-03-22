#!/bin/bash
INPUT_FILE="splitblock18"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock18
    fi
done < "$INPUT_FILE"