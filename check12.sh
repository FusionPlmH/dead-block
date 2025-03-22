#!/bin/bash
INPUT_FILE="splitblock12"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock12
    fi
done < "$INPUT_FILE"