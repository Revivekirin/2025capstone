import pandas as pd
from geopy.geocoders import Nominatim
import time

def add_coordinates_to_shodan_data(csv_path, save=True, sleep_sec=1):
    df = pd.read_csv(csv_path)
    geolocator = Nominatim(user_agent="geoapi")

    def get_lat_lon(row):
        if pd.notna(row.get("latitude")) and pd.notna(row.get("longitude")):
            return pd.Series([row["latitude"], row["longitude"]])
        try:
            location = geolocator.geocode(f"{row['region_code']}, {row['country_code']}", timeout=10)
            if location:
                print(f"[+] Geocoding {row['group']}, {row['domain']} -> {location.latitude}, {location.longitude}")
                time.sleep(sleep_sec)
                return pd.Series([location.latitude, location.longitude])
        except Exception as e:
            print(f"[!] Geocode error for {row['group']}, {row['domain']}: {e}")
        return pd.Series([None, None])

    df[['latitude', 'longitude']] = df.apply(get_lat_lon, axis=1)

    if save:
        df.to_csv(csv_path, index=False)
        print(f"[완료] 좌표가 추가된 파일이 저장되었습니다: {csv_path}")
    return df
