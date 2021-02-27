ps -e | grep -w $1 | awk '{print $1}' | xargs kill -9 
