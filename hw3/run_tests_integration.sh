# BEFORE RUNNING THIS TEST YOU HAVE TO RUN HTTP-SERVER WITH THE FOLLOWING PARAMETERS:
# - ip-address http://127.0.0.1
# - port 8080

# Run Python unittest in './tests/integration' folder.
python -m unittest discover -v -s ./tests/integration
