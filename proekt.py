import requests
import json
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional
import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, font
import threading

# ==================== КОНСТАНТЫ И КОНФИГУРАЦИЯ ====================

API_KEY = "ce5a102264928bf6141e12264"  # Получите на exchangerate-api.com
BASE_CURRENCY = "RUB"
CACHE_FILE = "exchange_rates_cache.json"
CACHE_DURATION_HOURS = 24

# ==================== МОДЕЛИ ДАННЫХ ====================

@dataclass
class ConversionResult:
    """Результат конвертации"""
    amount: float
    from_unit: str
    to_unit: str
    result: float
    timestamp: datetime
    rate: Optional[float] = None

# ==================== КЛАСС ДЛЯ РАБОТЫ С API КУРСОВ ВАЛЮТ ====================

class CurrencyConverter:
    def __init__(self, api_key: str, base_currency: str = "RUB"):
        self.api_key = api_key
        self.base_currency = base_currency
        self.rates: Dict[str, float] = {}
        self.last_update: Optional[datetime] = None
        self.api_url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{base_currency}"
        
    def _load_from_cache(self) -> bool:
        """Загружает курсы из кэша"""
        if not os.path.exists(CACHE_FILE):
            return False
            
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            cache_time = datetime.fromisoformat(data['timestamp'])
            if datetime.now() - cache_time < timedelta(hours=CACHE_DURATION_HOURS):
                self.rates = data['rates']
                self.last_update = cache_time
                return True
        except Exception as e:
            print(f"Ошибка при загрузке кэша: {e}")
            
        return False
        
    def _save_to_cache(self):
        """Сохраняет курсы в кэш"""
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'base': self.base_currency,
                'rates': self.rates
            }
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка при сохранении в кэш: {e}")
    
    def fetch_rates(self) -> bool:
        """Получает актуальные курсы с API"""
        # Сначала пробуем загрузить из кэша
        if self._load_from_cache():
            return True
            
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data['result'] == 'success':
                self.rates = data['conversion_rates']
                self.last_update = datetime.now()
                self._save_to_cache()
                return True
            else:
                return False
                
        except requests.exceptions.RequestException:
            return False
        except json.JSONDecodeError:
            return False
    
    def convert(self, from_currency: str, to_currency: str, amount: float) -> ConversionResult:
        """Конвертирует сумму из одной валюты в другую"""
        if not self.rates:
            raise ValueError("Курсы валют не загружены. Сначала вызовите fetch_rates()")
        
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        if from_currency not in self.rates or to_currency not in self.rates:
            available = list(self.rates.keys())[:20]
            raise ValueError(f"Неизвестная валюта. Доступные: {', '.join(available)}...")
        
        # Конвертация через базовую валюту
        if from_currency == self.base_currency:
            rate = self.rates[to_currency]
            result = amount * rate
        elif to_currency == self.base_currency:
            rate = 1 / self.rates[from_currency]
            result = amount * rate
        else:
            # Конвертация через две стадии
            amount_in_base = amount / self.rates[from_currency]
            result = amount_in_base * self.rates[to_currency]
            rate = result / amount
        
        return ConversionResult(
            amount=amount,
            from_unit=from_currency,
            to_unit=to_currency,
            result=result,
            timestamp=datetime.now(),
            rate=rate if 'rate' in locals() else self.rates[to_currency]
        )
    
    def get_available_currencies(self) -> List[str]:
        """Возвращает список доступных валют"""
        return list(self.rates.keys())

# ==================== КЛАСС ДЛЯ КОНВЕРТАЦИИ ЕДИНИЦ ИЗМЕРЕНИЯ ====================

class UnitConverter:
    """Конвертер различных единиц измерения"""
    
    # Коэффициенты конвертации (к базовым единицам)
    CONVERSION_FACTORS = {
        # Длина (базовая: метр)
        'Длина': {
            'мм': 0.001, 
            'см': 0.01, 
            'м': 1.0, 
            'км': 1000.0,
            'дюйм': 0.0254, 
            'фут': 0.3048, 
            'ярд': 0.9144, 
            'миля': 1609.34,
            'морская миля': 1852.0
        },
        # Масса (базовая: килограмм)
        'Масса': {
            'мг': 0.000001, 
            'г': 0.001, 
            'кг': 1.0, 
            'т': 1000.0,
            'центнер': 100.0,
            'унция': 0.0283495, 
            'фунт': 0.453592,
            'карат': 0.0002
        },
        # Температура (особый случай)
        'Температура': {
            '°C': 'celsius', 
            '°F': 'fahrenheit', 
            'K': 'kelvin'
        },
        # Площадь (базовая: квадратный метр)
        'Площадь': {
            'мм²': 0.000001,
            'см²': 0.0001,
            'м²': 1.0, 
            'км²': 1000000.0, 
            'га': 10000.0,
            'сотка': 100.0,
            'акр': 4046.86, 
            'фут²': 0.092903,
            'дюйм²': 0.00064516
        },
        # Скорость (базовая: м/с)
        'Скорость': {
            'м/с': 1.0, 
            'км/ч': 0.277778, 
            'миль/ч': 0.44704,
            'узлы': 0.514444,
            'фут/с': 0.3048
        },
        # Объем (базовая: литр)
        'Объем': {
            'мл': 0.001,
            'л': 1.0,
            'м³': 1000.0,
            'см³': 0.001,
            'галлон US': 3.78541,
            'галлон UK': 4.54609,
            'пинта US': 0.473176,
            'пинта UK': 0.568261,
            'жидкая унция': 0.0295735,
            'баррель нефтяной': 158.987
        },
        # Давление (базовая: Паскаль)
        'Давление': {
            'Па': 1.0,
            'кПа': 1000.0,
            'МПа': 1000000.0,
            'бар': 100000.0,
            'атм': 101325.0,
            'мм рт.ст.': 133.322,
            'psi': 6894.76
        },
        # Энергия (базовая: Джоуль)
        'Энергия': {
            'Дж': 1.0,
            'кДж': 1000.0,
            'МДж': 1000000.0,
            'ккал': 4184.0,
            'кал': 4.184,
            'кВт·ч': 3600000.0,
            'эВ': 1.60218e-19
        },
        # Мощность (базовая: Ватт)
        'Мощность': {
            'Вт': 1.0,
            'кВт': 1000.0,
            'МВт': 1000000.0,
            'л.с.': 735.499,
            'л.с. (англ.)': 745.7
        },
        # Время (базовая: секунда)
        'Время': {
            'нс': 1e-9,
            'мкс': 1e-6,
            'мс': 0.001,
            'с': 1.0,
            'мин': 60.0,
            'ч': 3600.0,
            'день': 86400.0,
            'неделя': 604800.0,
            'месяц': 2592000.0,  # 30 дней
            'год': 31536000.0  # 365 дней
        }
    }
    
    # Русские названия для английских сокращений
    UNIT_NAMES = {
        'мм': 'миллиметр',
        'см': 'сантиметр',
        'м': 'метр',
        'км': 'километр',
        'дюйм': 'дюйм',
        'фут': 'фут',
        'ярд': 'ярд',
        'миля': 'миля',
        'морская миля': 'морская миля',
        'мг': 'миллиграмм',
        'г': 'грамм',
        'кг': 'килограмм',
        'т': 'тонна',
        'центнер': 'центнер',
        'унция': 'унция',
        'фунт': 'фунт',
        'карат': 'карат',
        '°C': 'градус Цельсия',
        '°F': 'градус Фаренгейта',
        'K': 'Кельвин',
        'мм²': 'квадратный миллиметр',
        'см²': 'квадратный сантиметр',
        'м²': 'квадратный метр',
        'км²': 'квадратный километр',
        'га': 'гектар',
        'сотка': 'сотка',
        'акр': 'акр',
        'фут²': 'квадратный фут',
        'дюйм²': 'квадратный дюйм',
        'м/с': 'метр в секунду',
        'км/ч': 'километр в час',
        'миль/ч': 'миля в час',
        'узлы': 'узел',
        'фут/с': 'фут в секунду',
        'мл': 'миллилитр',
        'л': 'литр',
        'м³': 'кубический метр',
        'см³': 'кубический сантиметр',
        'галлон US': 'американский галлон',
        'галлон UK': 'английский галлон',
        'пинта US': 'американская пинта',
        'пинта UK': 'английская пинта',
        'жидкая унция': 'жидкая унция',
        'баррель нефтяной': 'нефтяной баррель',
        'Па': 'Паскаль',
        'кПа': 'килоПаскаль',
        'МПа': 'мегаПаскаль',
        'бар': 'бар',
        'атм': 'атмосфера',
        'мм рт.ст.': 'миллиметр ртутного столба',
        'psi': 'фунт-сила на квадратный дюйм',
        'Дж': 'Джоуль',
        'кДж': 'килоДжоуль',
        'МДж': 'мегаДжоуль',
        'ккал': 'килокалория',
        'кал': 'калория',
        'кВт·ч': 'киловатт-час',
        'эВ': 'электронвольт',
        'Вт': 'Ватт',
        'кВт': 'килоВатт',
        'МВт': 'мегаВатт',
        'л.с.': 'лошадиная сила',
        'л.с. (англ.)': 'лошадиная сила (англ.)',
        'нс': 'наносекунда',
        'мкс': 'микросекунда',
        'мс': 'миллисекунда',
        'с': 'секунда',
        'мин': 'минута',
        'ч': 'час',
        'день': 'день',
        'неделя': 'неделя',
        'месяц': 'месяц',
        'год': 'год'
    }
    
    @classmethod
    def get_unit_type(cls, unit: str) -> Optional[str]:
        """Определяет тип единицы измерения"""
        for unit_type, units in cls.CONVERSION_FACTORS.items():
            if unit in units:
                return unit_type
        return None
    
    @classmethod
    def convert(cls, value: float, from_unit: str, to_unit: str) -> ConversionResult:
        """Конвертирует значение из одних единиц в другие"""
        from_unit_type = cls.get_unit_type(from_unit)
        to_unit_type = cls.get_unit_type(to_unit)
        
        if not from_unit_type or not to_unit_type:
            raise ValueError(f"Неизвестная единица измерения: {from_unit} или {to_unit}")
        
        if from_unit_type != to_unit_type:
            raise ValueError(f"Несовместимые единицы: {from_unit} ({from_unit_type}) и {to_unit} ({to_unit_type})")
        
        # Особый случай: температура
        if from_unit_type == 'Температура':
            result = cls._convert_temperature(value, from_unit, to_unit)
        else:
            # Обычная конвертация через базовые единицы
            factors = cls.CONVERSION_FACTORS[from_unit_type]
            value_in_base = value * factors[from_unit]
            result = value_in_base / factors[to_unit]
        
        return ConversionResult(
            amount=value,
            from_unit=from_unit,
            to_unit=to_unit,
            result=result,
            timestamp=datetime.now()
        )
    
    @staticmethod
    def _convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
        """Конвертирует температуру"""
        # Сначала конвертируем в Цельсии
        if from_unit == '°C':
            celsius = value
        elif from_unit == '°F':
            celsius = (value - 32) * 5/9
        elif from_unit == 'K':
            celsius = value - 273.15
        else:
            raise ValueError(f"Неизвестная единица температуры: {from_unit}")
        
        # Затем конвертируем из Цельсиев в нужную единицу
        if to_unit == '°C':
            return celsius
        elif to_unit == '°F':
            return (celsius * 9/5) + 32
        elif to_unit == 'K':
            return celsius + 273.15
        else:
            raise ValueError(f"Неизвестная единица температуры: {to_unit}")
    
    @classmethod
    def get_available_units(cls):
        """Возвращает словарь доступных единиц измерения"""
        return cls.CONVERSION_FACTORS
    
    @classmethod
    def get_full_unit_name(cls, unit_code: str) -> str:
        """Возвращает полное название единицы измерения"""
        return cls.UNIT_NAMES.get(unit_code, unit_code)

# ==================== ГРАФИЧЕСКИЙ ИНТЕРФЕЙС ====================

class ConverterGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Конвертер валют и единиц измерения")
        self.root.geometry("1000x750")
        self.root.configure(bg='#f0f0f0')
        
        # Инициализация конвертеров
        self.currency_converter = CurrencyConverter(API_KEY, BASE_CURRENCY)
        self.unit_converter = UnitConverter()
        self.history: List[ConversionResult] = []
        
        # Стили
        self.setup_styles()
        
        # Загрузка курсов в фоновом режиме
        self.load_rates_in_background()
        
        # Создание интерфейса
        self.create_widgets()
        
    def setup_styles(self):
        """Настройка стилей для виджетов"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Настраиваем цвета
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), background='#f0f0f0')
        style.configure('Subtitle.TLabel', font=('Arial', 12), background='#f0f0f0')
        style.configure('Result.TLabel', font=('Arial', 14, 'bold'), foreground='#2c3e50')
        
        # Цвета для разных категорий
        style.configure('Length.TLabel', background='#e8f4f8')
        style.configure('Weight.TLabel', background='#f8e8f4')
        style.configure('Temp.TLabel', background='#fff8e8')
        
    def load_rates_in_background(self):
        """Загрузка курсов валют в фоновом режиме"""
        def load():
            success = self.currency_converter.fetch_rates()
            if success:
                self.root.after(0, lambda: self.status_label.config(
                    text=f"Курсы загружены. Доступно {len(self.currency_converter.get_available_currencies())} валют",
                    foreground='green'
                ))
            else:
                self.root.after(0, lambda: self.status_label.config(
                    text="Не удалось загрузить курсы. Используется кэш или демо-режим",
                    foreground='red'
                ))
                self.setup_demo_mode()
        
        thread = threading.Thread(target=load)
        thread.daemon = True
        thread.start()
    
    def setup_demo_mode(self):
        """Настройка демо-режима с фиксированными курсами"""
        demo_rates = {
            'USD': 0.011, 'EUR': 0.010, 'GBP': 0.0085,
            'JPY': 1.65, 'CNY': 0.079, 'RUB': 1.0,
            'CAD': 0.015, 'AUD': 0.016, 'CHF': 0.0095,
            'INR': 0.92, 'BRL': 0.055, 'MXN': 0.18,
            'UAH': 0.42, 'KZT': 5.15, 'BYN': 0.035
        }
        
        # Обновляем курсы в конвертере
        self.currency_converter.rates = demo_rates
        self.currency_converter.last_update = datetime.now()
    
    def create_widgets(self):
        """Создание всех виджетов интерфейса"""
        # Основной фрейм
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        title_label = ttk.Label(
            main_frame,
            text="КОНВЕРТЕР ВАЛЮТ И ЕДИНИЦ ИЗМЕРЕНИЯ",
            style='Title.TLabel'
        )
        title_label.pack(pady=(0, 20))
        
        # Создание Notebook (вкладок)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Создание вкладок
        self.create_currency_tab()
        self.create_units_tab()
        self.create_history_tab()
        self.create_info_tab()
        
        # Статус бар
        self.status_label = ttk.Label(
            main_frame,
            text="Загрузка курсов валют...",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        
        # Кнопка обновления
        update_btn = ttk.Button(
            main_frame,
            text="🔄 Обновить курсы валют",
            command=self.update_rates
        )
        update_btn.pack(pady=(10, 0))
    
    def create_currency_tab(self):
        """Создание вкладки для конвертации валют"""
        currency_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(currency_frame, text="💱 Конвертация валют")
        
        # Выбор валют
        currency_top_frame = ttk.Frame(currency_frame)
        currency_top_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Из валюты
        ttk.Label(currency_top_frame, text="Из валюты:", font=('Arial', 11)).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.from_currency = ttk.Combobox(currency_top_frame, width=15, font=('Arial', 11))
        self.from_currency.grid(row=1, column=0, padx=(0, 20))
        self.from_currency.set("RUB")
        
        # В валюту
        ttk.Label(currency_top_frame, text="В валюту:", font=('Arial', 11)).grid(row=0, column=1, sticky=tk.W, pady=(0, 5))
        self.to_currency = ttk.Combobox(currency_top_frame, width=15, font=('Arial', 11))
        self.to_currency.grid(row=1, column=1, padx=(0, 20))
        self.to_currency.set("USD")
        
        # Кнопка смены валют
        swap_btn = ttk.Button(currency_top_frame, text="↔ Поменять", width=12, command=self.swap_currencies)
        swap_btn.grid(row=1, column=2, padx=(10, 20))
        
        # Сумма
        ttk.Label(currency_top_frame, text="Сумма:", font=('Arial', 11)).grid(row=0, column=3, sticky=tk.W, pady=(0, 5))
        self.amount_var = tk.StringVar(value="100")
        amount_entry = ttk.Entry(currency_top_frame, textvariable=self.amount_var, width=20, font=('Arial', 11))
        amount_entry.grid(row=1, column=3)
        
        # Кнопка конвертации
        convert_btn = ttk.Button(currency_frame, text="▶ Конвертировать", command=self.convert_currency)
        convert_btn.pack(pady=(0, 20))
        
        # Фрейм для результатов
        result_frame = ttk.LabelFrame(currency_frame, text="Результат", padding="15")
        result_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Результат
        self.result_label = ttk.Label(
            result_frame,
            text="Результат появится здесь",
            font=('Arial', 16, 'bold'),
            foreground='#2c3e50',
            anchor=tk.CENTER
        )
        self.result_label.pack(fill=tk.X, pady=(0, 10))
        
        # Курс
        self.rate_label = ttk.Label(
            result_frame,
            text="",
            font=('Arial', 11),
            foreground='#666',
            anchor=tk.CENTER
        )
        self.rate_label.pack(fill=tk.X)
        
        # Обновляем список валют после загрузки
        self.root.after(1000, self.update_currency_list)
    
    def create_units_tab(self):
        """Создание вкладки для конвертации единиц измерения"""
        units_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(units_frame, text="📏 Конвертация единиц")
        
        # Выбор типа единиц
        type_frame = ttk.Frame(units_frame)
        type_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(type_frame, text="Тип единиц:", font=('Arial', 11)).pack(side=tk.LEFT, padx=(0, 10))
        self.unit_type_var = tk.StringVar()
        unit_types = list(self.unit_converter.get_available_units().keys())
        self.unit_type_combo = ttk.Combobox(
            type_frame, 
            textvariable=self.unit_type_var, 
            values=unit_types, 
            state="readonly", 
            width=20, 
            font=('Arial', 11)
        )
        self.unit_type_combo.pack(side=tk.LEFT)
        self.unit_type_combo.set(unit_types[0])
        self.unit_type_combo.bind('<<ComboboxSelected>>', self.on_unit_type_change)
        
        # Выбор единиц
        units_middle_frame = ttk.Frame(units_frame)
        units_middle_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Из единицы с полным названием
        from_frame = ttk.Frame(units_middle_frame)
        from_frame.grid(row=0, column=0, padx=(0, 20), sticky=tk.N)
        
        ttk.Label(from_frame, text="Из единицы:", font=('Arial', 11)).pack(anchor=tk.W, pady=(0, 5))
        self.from_unit = ttk.Combobox(from_frame, width=15, font=('Arial', 11))
        self.from_unit.pack()
        self.from_unit_name = ttk.Label(from_frame, text="", font=('Arial', 9), foreground='#666')
        self.from_unit_name.pack(anchor=tk.W, pady=(2, 0))
        
        # В единицу с полным названием
        to_frame = ttk.Frame(units_middle_frame)
        to_frame.grid(row=0, column=1, padx=(0, 20), sticky=tk.N)
        
        ttk.Label(to_frame, text="В единицу:", font=('Arial', 11)).pack(anchor=tk.W, pady=(0, 5))
        self.to_unit = ttk.Combobox(to_frame, width=15, font=('Arial', 11))
        self.to_unit.pack()
        self.to_unit_name = ttk.Label(to_frame, text="", font=('Arial', 9), foreground='#666')
        self.to_unit_name.pack(anchor=tk.W, pady=(2, 0))
        
        # Кнопка смены единиц
        swap_frame = ttk.Frame(units_middle_frame)
        swap_frame.grid(row=0, column=2, padx=(10, 20), sticky=tk.N)
        
        swap_units_btn = ttk.Button(swap_frame, text="↔", width=3, command=self.swap_units)
        swap_units_btn.pack(pady=(25, 0))
        
        # Значение
        value_frame = ttk.Frame(units_middle_frame)
        value_frame.grid(row=0, column=3, sticky=tk.N)
        
        ttk.Label(value_frame, text="Значение:", font=('Arial', 11)).pack(anchor=tk.W, pady=(0, 5))
        self.unit_amount_var = tk.StringVar(value="1")
        unit_amount_entry = ttk.Entry(value_frame, textvariable=self.unit_amount_var, width=20, font=('Arial', 11))
        unit_amount_entry.pack()
        
        # Кнопка конвертации
        convert_units_btn = ttk.Button(units_frame, text="▶ Конвертировать", command=self.convert_units)
        convert_units_btn.pack(pady=(0, 20))
        
        # Фрейм для результатов
        units_result_frame = ttk.LabelFrame(units_frame, text="Результат", padding="15")
        units_result_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Результат
        self.units_result_label = ttk.Label(
            units_result_frame,
            text="Результат появится здесь",
            font=('Arial', 16, 'bold'),
            foreground='#2c3e50',
            anchor=tk.CENTER
        )
        self.units_result_label.pack(fill=tk.X)
        
        # Обновляем список единиц для выбранного типа
        self.on_unit_type_change()
    
    def create_history_tab(self):
        """Создание вкладки истории конвертаций"""
        history_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(history_frame, text="📋 История")
        
        # Заголовок
        ttk.Label(history_frame, text="История конвертаций", font=('Arial', 14, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        
        # Текстовое поле для истории
        self.history_text = scrolledtext.ScrolledText(
            history_frame,
            width=90,
            height=25,
            font=('Consolas', 10),
            wrap=tk.WORD,
            background='#fafafa'
        )
        self.history_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Кнопки управления историей
        button_frame = ttk.Frame(history_frame)
        button_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(button_frame, text="🔄 Обновить", command=self.update_history).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🗑️ Очистить", command=self.clear_history).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="💾 Сохранить в файл", command=self.save_history).pack(side=tk.RIGHT)
        
        # Информация о истории
        self.history_info = ttk.Label(history_frame, text="Конвертации пока не производились", font=('Arial', 9))
        self.history_info.pack()
    
    def create_info_tab(self):
        """Создание информационной вкладки"""
        info_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(info_frame, text="ℹ️ Информация")
        
        # Основной контент
        content_frame = ttk.Frame(info_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        ttk.Label(
            content_frame,
            text="О программе",
            font=('Arial', 16, 'bold')
        ).pack(anchor=tk.W, pady=(0, 20))
        
        # Информационный текст
        info_text = """
Конвертер валют и единиц измерения
        
Функции:
• Конвертация валют по актуальным курсам
• Конвертация различных физических величин
• История всех операций
• Кэширование курсов на 24 часа
• Автообновление курсов

Доступные категории единиц измерения:
• Длина (мм, см, м, км, дюймы, футы, мили)
• Масса (мг, г, кг, т, унции, фунты)
• Температура (°C, °F, K)
• Площадь (мм², см², м², га, акры)
• Скорость (м/с, км/ч, мили/ч, узлы)
• Объем (мл, л, м³, галлоны, баррели)
• Давление (Па, кПа, бар, атм, мм рт.ст.)
• Энергия (Дж, кДж, ккал, кВт·ч)
• Мощность (Вт, кВт, л.с.)
• Время (нс, мкс, мс, с, мин, ч, дни, годы)

Для работы с валютами требуется API ключ от exchangerate-api.com
Бесплатный тариф: 1500 запросов в месяц
        """
        
        info_label = ttk.Label(
            content_frame,
            text=info_text.strip(),
            font=('Arial', 10),
            justify=tk.LEFT,
            background='#f9f9f9',
            relief=tk.SUNKEN,
            padding=15
        )
        info_label.pack(fill=tk.BOTH, expand=True)
        
        # Контактная информация
        ttk.Label(
            content_frame,
            text="\nДля получения API ключа посетите: https://www.exchangerate-api.com/",
            font=('Arial', 9, 'italic'),
            foreground='#666'
        ).pack(anchor=tk.W, pady=(10, 0))
    
    def update_currency_list(self):
        """Обновление списка доступных валют"""
        currencies = sorted(self.currency_converter.get_available_currencies())
        self.from_currency['values'] = currencies
        self.to_currency['values'] = currencies
    
    def on_unit_type_change(self, event=None):
        """Обновление списка единиц при изменении типа"""
        unit_type = self.unit_type_var.get()
        units = list(self.unit_converter.get_available_units().get(unit_type, {}).keys())
        
        self.from_unit['values'] = units
        self.to_unit['values'] = units
        
        if units:
            self.from_unit.set(units[0])
            if len(units) > 1:
                self.to_unit.set(units[1])
            else:
                self.to_unit.set(units[0])
            
            # Обновляем полные названия
            self.update_unit_names()
    
    def update_unit_names(self):
        """Обновление полных названий единиц измерения"""
        from_unit = self.from_unit.get()
        to_unit = self.to_unit.get()
        
        self.from_unit_name.config(
            text=self.unit_converter.get_full_unit_name(from_unit)
        )
        self.to_unit_name.config(
            text=self.unit_converter.get_full_unit_name(to_unit)
        )
    
    def swap_currencies(self):
        """Поменять местами выбранные валюты"""
        from_curr = self.from_currency.get()
        to_curr = self.to_currency.get()
        
        self.from_currency.set(to_curr)
        self.to_currency.set(from_curr)
    
    def swap_units(self):
        """Поменять местами выбранные единицы"""
        from_unit = self.from_unit.get()
        to_unit = self.to_unit.get()
        
        self.from_unit.set(to_unit)
        self.to_unit.set(from_unit)
        self.update_unit_names()
    
    def convert_currency(self):
        """Конвертация валюты"""
        try:
            from_curr = self.from_currency.get().upper()
            to_curr = self.to_currency.get().upper()
            amount = float(self.amount_var.get())
            
            result = self.currency_converter.convert(from_curr, to_curr, amount)
            self.history.append(result)
            
            # Форматирование чисел с разделителями тысяч
            formatted_amount = f"{result.amount:,.2f}".replace(',', ' ').replace('.', ',')
            formatted_result = f"{result.result:,.2f}".replace(',', ' ').replace('.', ',')
            
            # Обновляем результат
            self.result_label.config(
                text=f"{formatted_amount} {result.from_unit} = {formatted_result} {result.to_unit}"
            )
            
            if result.rate:
                rate1 = f"1 {from_curr} = {result.rate:.6f} {to_curr}"
                rate2 = f"1 {to_curr} = {1/result.rate:.6f} {from_curr}"
                self.rate_label.config(text=f"{rate1} | {rate2}")
            
            # Обновляем историю
            self.update_history()
            
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Ошибка ввода: {str(e)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка конвертации: {str(e)}")
    
    def convert_units(self):
        """Конвертация единиц измерения"""
        try:
            from_unit = self.from_unit.get()
            to_unit = self.to_unit.get()
            amount = float(self.unit_amount_var.get())
            
            result = self.unit_converter.convert(amount, from_unit, to_unit)
            self.history.append(result)
            
            # Форматирование результата
            if abs(result.result) >= 10000 or (0 < abs(result.result) < 0.001):
                formatted_result = f"{result.result:.4e}"
                formatted_amount = f"{result.amount:.4e}"
            else:
                formatted_result = f"{result.result:,.6g}".replace(',', ' ')
                formatted_amount = f"{result.amount:,.6g}".replace(',', ' ')
            
            # Обновляем результат
            self.units_result_label.config(
                text=f"{formatted_amount} {result.from_unit} = {formatted_result} {result.to_unit}"
            )
            
            # Обновляем историю
            self.update_history()
            
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Ошибка ввода: {str(e)}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка конвертации: {str(e)}")
    
    def update_rates(self):
        """Обновление курсов валют"""
        self.status_label.config(text="Обновление курсов...", foreground='blue')
        
        def load():
            success = self.currency_converter.fetch_rates()
            if success:
                self.root.after(0, lambda: self.status_label.config(
                    text=f"Курсы успешно обновлены! Доступно {len(self.currency_converter.get_available_currencies())} валют",
                    foreground='green'
                ))
                self.root.after(0, self.update_currency_list)
            else:
                self.root.after(0, lambda: self.status_label.config(
                    text="Не удалось обновить курсы",
                    foreground='red'
                ))
        
        thread = threading.Thread(target=load)
        thread.daemon = True
        thread.start()
    
    def update_history(self):
        """Обновление истории конвертаций"""
        self.history_text.delete(1.0, tk.END)
        
        if not self.history:
            self.history_info.config(text="Конвертации пока не производились")
            return
        
        self.history_info.config(text=f"Всего конвертаций: {len(self.history)}")
        
        # Выводим историю в обратном порядке (последние сверху)
        for i, conv in enumerate(reversed(self.history), 1):
            time_str = conv.timestamp.strftime("%d.%m.%Y %H:%M:%S")
            
            if conv.rate:
                # Конвертация валюты
                amount_str = f"{conv.amount:,.2f}".replace(',', ' ')
                result_str = f"{conv.result:,.2f}".replace(',', ' ')
                history_line = f"{i:3}. {time_str} | {amount_str:>12} {conv.from_unit:5} → {result_str:>12} {conv.to_unit:5}"
                history_line += f" | Курс: 1 {conv.from_unit} = {conv.rate:.6f} {conv.to_unit}\n"
            else:
                # Конвертация единиц
                amount_str = f"{conv.amount:,.6g}".replace(',', ' ')
                result_str = f"{conv.result:,.6g}".replace(',', ' ')
                history_line = f"{i:3}. {time_str} | {amount_str:>12} {conv.from_unit:5} → {result_str:>12} {conv.to_unit:5}\n"
            
            self.history_text.insert(tk.END, history_line)
    
    def clear_history(self):
        """Очистка истории конвертаций"""
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите очистить историю?"):
            self.history.clear()
            self.update_history()
    
    def save_history(self):
        """Сохранение истории в файл"""
        try:
            filename = f"history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("История конвертаций\n")
                f.write("=" * 60 + "\n\n")
                
                for i, conv in enumerate(reversed(self.history), 1):
                    time_str = conv.timestamp.strftime("%d.%m.%Y %H:%M:%S")
                    
                    if conv.rate:
                        line = f"{i:3}. {time_str} | {conv.amount:,.2f} {conv.from_unit} → {conv.result:,.2f} {conv.to_unit}"
                        line += f" | Курс: 1 {conv.from_unit} = {conv.rate:.6f} {conv.to_unit}\n"
                    else:
                        line = f"{i:3}. {time_str} | {conv.amount:,.6g} {conv.from_unit} → {conv.result:,.6g} {conv.to_unit}\n"
                    
                    f.write(line)
            
            messagebox.showinfo("Успех", f"История сохранена в файл: {filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить историю: {str(e)}")
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()

# ==================== ТОЧКА ВХОДА ====================

if __name__ == "__main__":
    # Для работы без API ключа (демо-режим)
    if API_KEY == "ваш_api_ключ" or API_KEY == "ce5a102264928bf6141e12264":
        print("ВНИМАНИЕ: Установите API ключ в переменной API_KEY")
        print("Получите бесплатный ключ на exchangerate-api.com")
        print("Запускаю в демо-режиме с тестовыми курсами...")
    
    # Запуск графического интерфейса
    app = ConverterGUI()
    app.run()