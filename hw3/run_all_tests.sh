# BEFORE RUNNING THIS TEST YOU HAVE TO RUN:
#   - Scoring Api Server
#   - Redis Server
#
# AND SET IN ENVIRONMENT VARIABLE THE FOLLOWING PARAMETERS:
#   - API_URL='<host>:<port>'
#   - REDIS_HOST='<host>'
#   - REDIS_PORT='<port>'
#   - REDIS_PASSWORD='<password>'
#

# Set in Environment Variable
export API_URL='http://127.0.0.1:8080/method/' \
       REDIS_HOST='localhost'

# Run Python unittest in './tests/' folder.
python -m unittest discover -v -s ./tests/

# Unset from Environment Variable
unset API_URL \
      REDIS_HOST
