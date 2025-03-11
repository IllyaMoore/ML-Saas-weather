
import datetime as dt
import datetime as dt
import json
import requests
from flask import Flask, jsonify, request
from datetime import datetime
import google.generativeai as genai

API_TOKEN = "H123"
RSA_API_KEY = "67056824d05a455eb9d152559241502"
GEMINI_API_KEY = "AIzaSyAqTUVnoP_fFhh0qrDsJjqkfQK5LhNrWu8"

genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)

def generate_forecast(location: str, data: str, aqi: str):
    url_base_url = "http://api.weatherapi.com"
    url_api = "v1"
    url_endpoint = ""
    url_key = f"?key={RSA_API_KEY}"
    url_location = ""
    url_data = ""
    url_aqi = ""
    
    date_datatime = datetime.strptime(data, "%Y-%m-%d")
    now = datetime.now()
    
    if date_datatime.date() == now.date():
        url_endpoint = "current.json"
    elif date_datatime.date() < now.date():
        url_endpoint = "history.json"
    else:
        url_endpoint = "future.json"
    
    if location:
        url_location = f"&q={location}"
    if data:
        url_data = f"&dt={data}"
    if aqi:
        url_aqi = f"&aqi={aqi}"
    
    url = f"{url_base_url}/{url_api}/{url_endpoint}{url_key}{url_location}{url_data}{url_aqi}"
    payload = {}
    headers = {}
    response = requests.request("GET", url, headers=headers, data=payload)
    return json.loads(response.text)

def analyze_drone_flying_conditions(weather_data, location, date):
    """Аналізує погодні умови для польотів дронів через Gemini"""
    
    try:
        if 'current' in weather_data:

            weather_condition = weather_data['current']['condition']['text']
            wind_kph = weather_data['current']['wind_kph']
            precipitation_mm = weather_data['current']['precip_mm']
            temperature = weather_data['current']['temp_c']
            visibility = weather_data['current'].get('vis_km', 'немає даних')
        elif 'forecast' in weather_data:

            day_data = weather_data['forecast']['forecastday'][0]['day']
            weather_condition = day_data['condition']['text']
            wind_kph = day_data['maxwind_kph']
            precipitation_mm = day_data['totalprecip_mm']
            temperature = day_data['avgtemp_c']

        else:
            return {"error": "Неможливо отримати потрібні погодні дані"
        
        # Промпт для Gemini
        prompt = f"""
        На основі наступних погодних умов, оціни та поясни, чи можна безпечно запускати дрони в місті {location} на дату {date}:
        
        Погодні умови: {weather_condition}
        Швидкість вітру: {wind_kph} км/год
        Опади: {precipitation_mm} мм
        Температура: {temperature}°C
        
        Надай детальну відповідь щодо безпеки польотів дронів за цих умов, включаючи:
        1. Чи безпечно літати дронам (так/ні/з обмеженнями)
        2. Основні фактори ризику, якщо такі є
        3. Рекомендації для операторів дронів
        4. Звіт не має бути дуже обшиним, старайся лаконічно оцінити погодні данні 
        """
        
        # Виклик Gemini API
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        return {
            "drone_flying_analysis": response.text,
            "weather_data_analyzed": {
                "weather_condition": weather_condition,
                "wind_kph": wind_kph,
                "precipitation_mm": precipitation_mm,
                "temperature": temperature,
                "visibility": visibility
            }
        }
    
    except Exception as e:
        return {
            "error": f"Помилка: {str(e)}",
            "suggestion": "Перевірити налаштування API"
        }

class InvalidUsage(Exception):
    status_code = 400
    
    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
    
    def to_dict(self):
        rv = dict(self.payload or ())
        rv["message"] = self.message
        return rv

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response

@app.route("/")
def home_page():
    return "<p><h2>KMA L2: Python Saas з інтеграцією Gemini LLM.</h2></p>"

@app.route(
    "/content/api/v1/integration/generate",
    methods=["POST"],
)
def weather_endpoint():
    start_dt = dt.datetime.now()
    json_data = request.get_json()
    
    if json_data.get("token") is None:
        raise InvalidUsage("token is required", status_code=400)
    
    token = json_data.get("token")
    if token != API_TOKEN:
        raise InvalidUsage("wrong API token", status_code=403)
    
    name = ""
    if json_data.get("requester_name"):
        name = json_data.get("requester_name")
    
    location = ""
    if json_data.get("location"):
        location = json_data.get("location")
    
    data = ""
    if json_data.get("data"):
        data = json_data.get("data")
    
    aqi = ""
    if json_data.get("aqi"):
        aqi = json_data.get("aqi")
    
    weather = generate_forecast(location, data, aqi)
    
    drone_analysis = analyze_drone_flying_conditions(weather, location, data)
    
    end_dt = dt.datetime.now()
    
    result = {
        "event_start_datetime": start_dt.isoformat(),
        "event_finished_datetime": end_dt.isoformat(),
        "event_duration": str(end_dt - start_dt),
        "requester_name": name,
        "weather": weather,
        "drone_flying_conditions": drone_analysis
    }
    
    return result

if __name__ == "__main__":
    app.run(debug=True)
