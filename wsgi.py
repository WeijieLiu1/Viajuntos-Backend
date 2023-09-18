from app import app
import os

if __name__ == '__main__':
    # Secret key for signing cookies
    #os.system('source testEnv.sh')
    #print("Starting API server... "+5000)
    #print("Starting API server... "+os.environ.get('API_PORT'))
    # app.run(host='0.0.0.0', port=int(os.environ.get('API_PORT')), debug=bool(os.getenv('API_DEBUG')))
    app.run(host='localhost', port=int(os.environ.get('API_PORT') or 5000), debug=bool(os.getenv('API_DEBUG')))
    #app.run(host='0.0.0.0', port=5000, debug=bool(os.getenv('API_DEBUG')))