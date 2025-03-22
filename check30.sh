#!/bin/bash
INPUT_FILE="splitblock30"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock30
    fi
done < "$INPUT_FILE"