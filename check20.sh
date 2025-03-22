#!/bin/bash
INPUT_FILE="splitblock20"
while IFS= read -r domain; do
    RESULT=$(pyfunceble -s -d "$domain")
    if [ "$RESULT" != "ACTIVE" ]; then
         echo "$domain" >> deadblock20
    fi
done < "$INPUT_FILE"