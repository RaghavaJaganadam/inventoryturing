from app import create_app
from datetime import date

app = create_app('development')

# Add template global for current date
@app.template_global()
def today():
    return date.today()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)