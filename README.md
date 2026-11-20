# ESP32 Data Monitor

Program do odbioru danych z ESP32 przez USB (port szeregowy COM) i prezentowania ich na wykresach w czasie rzeczywistym.

## Funkcje

- automatyczne wykrywanie portów COM i wybór prędkości transmisji;
- wykres wielu kanałów jednocześnie;
- odczyt CSV, pól nazwanych oraz obiektów JSON;
- bieżące wartości liczbowe, pauza i czyszczenie wykresu;
- eksport zebranych danych do pliku CSV;
- instalator Windows 10/11 tworzony automatycznie przez GitHub Actions.

Interfejs programu jest po polsku.

### Informacja o antywirusach

Program jest pakowany do EXE przez PyInstaller. Niektóre antywirusy mogą heurystycznie oznaczać aplikacje zbudowane tym narzędziem; samo ostrzeżenie nie rozstrzyga, czy plik jest złośliwy. Workflow buduje własny bootloader PyInstaller ze źródeł, co według dokumentacji PyInstaller może ograniczyć fałszywe wykrycia gotowych bootloaderów. Nie daje to gwarancji braku alarmów. Plik nie jest podpisany certyfikatem Authenticode.

## Pobranie instalatora

Po zakończeniu kompilacji otwórz kartę **Actions** w repozytorium, wybierz ostatnie wykonanie workflow **Buduj instalator Windows**, a następnie pobierz artefakt **ESP32-Data-Monitor-Installer**. W ZIP znajduje się plik instalacyjny EXE.

Workflow uruchamia się automatycznie po zmianie kodu w gałęzi main. Można go też uruchomić ręcznie przez Actions → Buduj instalator Windows → Run workflow.

## Podłączenie ESP32

1. Podłącz ESP32 przewodem USB do komputera. Użyj przewodu obsługującego transmisję danych.
2. Zamknij Arduino Serial Monitor lub inne aplikacje, które mogą zajmować port COM.
3. Uruchom ESP32 Data Monitor.
4. Wybierz port COM oraz prędkość zgodną z ustawieniem Serial.begin(...) w ESP32 (najczęściej 115200).
5. Kliknij **Połącz**.

Program oczekuje tekstowych wierszy zakończonych znakiem nowej linii (Serial.println). Obsługiwane przykładowe formaty:

CSV bez nagłówka:
    
    23.5,4.2,12.8
    23.6,4.3,12.9

CSV z nagłówkiem:
    
    temperatura,ciśnienie,napięcie
    23.5,4.2,12.8
    23.6,4.3,12.9

Pola nazwane:
    
    TEMP:23.5; PRESS:4.2; VOLT:12.8
    TEMP:23.6; PRESS:4.3; VOLT:12.9

JSON:
    
    {"temperatura":23.5,"cisnienie":4.2,"napiecie":12.8}
    {"temperatura":23.6,"cisnienie":4.3,"napiecie":12.9}

Nazwy z nagłówka CSV lub pól JSON/nazwanych stają się nazwami kanałów na wykresie. W CSV bez nagłówka kanały otrzymują nazwy CH1, CH2 itd.

### Przykładowy szkic ESP32 (Arduino IDE)

    void setup() {
      Serial.begin(115200);
    }

    void loop() {
      float temperatura = 23.5;
      float cisnienie = 4.2;
      float napiecie = 12.8;

      Serial.print(temperatura, 2);
      Serial.print(",");
      Serial.print(cisnienie, 2);
      Serial.print(",");
      Serial.println(napiecie, 2);

      delay(100);
    }

## Kompilacja lokalna (opcjonalnie)

Wymagany jest Python 3.11 lub 3.12 oraz Inno Setup 6.

    python -m pip install -r requirements.txt
    build_windows.bat

Gotowy instalator pojawi się w katalogu installer/Output.

## Struktura

- app/ – aplikacja, parser danych i obsługa portu szeregowego;
- tests/ – testy parsera;
- installer/ – skrypt instalatora Inno Setup;
- .github/workflows/ – automatyczna kompilacja na Windows.
