import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import seaborn as sns
from datetime import datetime
import json
import logging
from typing import Dict, List, Optional
import io
from aiogram.types import BufferedInputFile

logger = logging.getLogger(__name__)

# Настройка стиля графиков
plt.style.use("seaborn-v0_8")
sns.set_palette("husl")


class ChartCreator:
    """Создатель графиков для PizdaBot (в памяти)"""

    def __init__(self):
        # Настройка matplotlib для работы без GUI
        plt.switch_backend("Agg")

        # Настройка шрифтов для поддержки русского языка
        plt.rcParams["font.family"] = ["DejaVu Sans", "Arial", "sans-serif"]
        plt.rcParams["axes.unicode_minus"] = False

    async def create_growth_chart(self, chart_data: dict) -> BufferedInputFile:
        """
        Создает график роста в памяти и возвращает BufferedInputFile для aiogram

        Args:
            chart_data: Словарь с данными для графика

        Returns:
            BufferedInputFile: Файл для отправки в Telegram
        """
        try:
            # Подготовка данных
            timeline_data = chart_data["data"]
            if not timeline_data:
                raise ValueError("Нет данных для построения графика")

            # Конвертируем данные в DataFrame
            df = pd.DataFrame(timeline_data)
            df["datetime"] = pd.to_datetime(df["date"])
            df = df.sort_values("datetime")

            # Создаем график
            fig, ax = plt.subplots(figsize=(12, 6))

            # Настройка цвета
            color = chart_data.get("color", "#2196F3")

            # Строим линейный график
            ax.plot(
                df["datetime"],
                df["count"],
                color=color,
                linewidth=2.5,
                marker="o",
                markersize=4,
                markerfacecolor=color,
                markeredgecolor="white",
                markeredgewidth=1,
            )

            # Заливка под графиком
            ax.fill_between(df["datetime"], df["count"], alpha=0.3, color=color)

            # Настройка осей
            ax.set_xlabel("Время", fontsize=12, fontweight="bold")
            ax.set_ylabel(
                chart_data.get("y_label", "Значения"), fontsize=12, fontweight="bold"
            )
            ax.set_title(chart_data["title"], fontsize=14, fontweight="bold", pad=20)

            # Форматирование оси времени
            if len(df) > 20:
                ax.xaxis.set_major_locator(
                    mdates.HourLocator(interval=max(1, len(df) // 10))
                )
            else:
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))

            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m\n%H:%M"))

            # Поворот подписей на оси X
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")

            # Сетка
            ax.grid(True, alpha=0.3, linestyle="--")

            # Статистика на графике
            current_value = df["count"].iloc[-1]
            if len(df) >= 2:
                growth = df["count"].iloc[-1] - df["count"].iloc[0]
                growth_text = f"Текущее: {current_value:,}\nИзменение: {growth:+,}"
            else:
                growth_text = f"Значение: {current_value:,}"

            ax.text(
                0.02,
                0.98,
                growth_text,
                transform=ax.transAxes,
                verticalalignment="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
                fontsize=10,
            )

            # Улучшение внешнего вида
            plt.tight_layout()

            # Сохраняем в память
            buf = io.BytesIO()
            plt.savefig(
                buf,
                format="png",
                dpi=150,
                bbox_inches="tight",
                facecolor="white",
                edgecolor="none",
            )
            buf.seek(0)
            plt.close()

            # Создаем BufferedInputFile
            filename = f"{chart_data['title'].replace(' ', '_')}.png"
            return BufferedInputFile(buf.getvalue(), filename=filename)

        except Exception as e:
            logger.error(f"Ошибка создания графика: {e}")
            plt.close("all")  # Закрываем все графики в случае ошибки
            raise


# Глобальный экземпляр создателя графиков
chart_creator = ChartCreator()


# Функции-хелперы
async def create_growth_chart(chart_data: dict) -> BufferedInputFile:
    """Создать график роста"""
    return await chart_creator.create_growth_chart(chart_data)


async def create_comparison_chart(chart_data: dict) -> BufferedInputFile:
    """Создать график сравнения"""
    return await chart_creator.create_comparison_chart(chart_data)
