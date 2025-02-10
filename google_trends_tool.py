import os
import json
import pandas as pd
from sqlalchemy import create_engine
from superagi.tools.base_tool import BaseTool
from pydantic import BaseModel, Field
from typing import Type, Optional, List
from superagi.resource_manager.file_manager import FileManager
from pytrends.request import TrendReq
import time
import random

class GoogleTrendsToolInput(BaseModel):
    keywords: List[str] = Field(..., description="List of keywords to search trends for.")
    timeframe: str = Field(default='now 7-d', description="Time range for trends (e.g., 'now 7-d', 'today 12-m').")
    geo: str = Field(default='', description="Geographical location code (e.g., 'US', 'RU'). Leave empty for worldwide trends.")
    save_format: str = Field(default='txt', description="Format to save the report: 'txt', 'csv', 'json', 'db'.")
    include_related_queries: bool = Field(default=True, description="Include related and rising queries in the report.")
    include_geo_analysis: bool = Field(default=True, description="Include geographical analysis in the report.")
    include_seasonality: bool = Field(default=True, description="Include seasonality analysis in the report.")

class GoogleTrendsTool(BaseTool):
    """
    Google Trends Tool with extended functionalities and multiple save formats.
    """
    name: str = "Google Trends Tool"
    args_schema: Type[BaseModel] = GoogleTrendsToolInput
    description: str = "Fetches trending search topics from Google Trends, compares keywords, includes related queries, and provides geographical and seasonal analysis with multiple save options."
    resource_manager: Optional[FileManager] = None

    def _execute(self, keywords: List[str], timeframe: str, geo: str, save_format: str, include_related_queries: bool, include_geo_analysis: bool, include_seasonality: bool):
        pytrends = TrendReq(hl='en-US', tz=360, retries=3, backoff_factor=0.4)
        
        combined_data = pd.DataFrame()
        report = ""

        for keyword in keywords:
            try:
                # Построение запроса к Google Trends
                pytrends.build_payload([keyword], timeframe=timeframe, geo=geo)
                data = pytrends.interest_over_time()

                if data.empty:
                    report += f"No trending data found for '{keyword}'.\n"
                    continue

                # Добавление данных в общий DataFrame
                data['keyword'] = keyword
                combined_data = pd.concat([combined_data, data.reset_index()], ignore_index=True)

                report += self._generate_trend_report(data, keyword)

                # Анализ связанных запросов
                if include_related_queries:
                    related_queries = pytrends.related_queries()
                    report += self._generate_related_queries_report(related_queries, keyword)

                # Географический анализ
                if include_geo_analysis:
                    geo_data = pytrends.interest_by_region(resolution='CITY', geo=geo)
                    report += self._generate_geo_report(geo_data, keyword)

                # Анализ сезонности
                if include_seasonality:
                    seasonality_data = self._analyze_seasonality(pytrends, keyword, geo)
                    report += self._generate_seasonality_report(seasonality_data, keyword)

                # Добавление случайной задержки между запросами
                time.sleep(random.uniform(2, 5))

            except Exception as e:
                report += f"Error fetching data for '{keyword}': {str(e)}\n"

        # Сохранение отчёта в выбранном формате
        filename_base = f"{'_'.join([k.replace(' ', '_') for k in keywords])}_trends_report"
        if save_format == 'csv':
            return self._save_to_csv(combined_data, f"{filename_base}.csv")
        elif save_format == 'json':
            return self._save_to_json(combined_data, f"{filename_base}.json")
        elif save_format == 'db':
            return self._save_to_db(combined_data, 'trends')
        else:
            return self._save_to_txt(report, f"{filename_base}.txt")

    def _generate_trend_report(self, data, keyword):
        report = f"Trends Report for '{keyword}':\n\n"
        report += "Date\t\tInterest\n"
        report += "-" * 30 + "\n"

        for date, value in data[keyword].items():
            report += f"{date.strftime('%Y-%m-%d')}\t{value}\n"

        report += "\n"
        return report

    def _generate_related_queries_report(self, related_queries, keyword):
        report = "\nRelated Queries:\n"
        report += "-" * 30 + "\n"

        if keyword in related_queries:
            top_queries = related_queries[keyword]['top']
            rising_queries = related_queries[keyword]['rising']

            if top_queries is not None:
                report += f"Top Related Queries for '{keyword}':\n"
                for _, row in top_queries.iterrows():
                    report += f"{row['query']} - {row['value']}\n"
            else:
                report += f"No top related queries found for '{keyword}'.\n"

            if rising_queries is not None:
                report += f"\nRising Queries for '{keyword}':\n"
                for _, row in rising_queries.iterrows():
                    report += f"{row['query']} - {row['value']}\n"
            else:
                report += f"No rising queries found for '{keyword}'.\n"
        else:
            report += f"No related queries data available for '{keyword}'.\n"

        report += "\n"
        return report

    def _generate_geo_report(self, geo_data, keyword):
        report = "\nGeographical Analysis:\n"
        report += "-" * 30 + "\n"

        if geo_data.empty:
            return "No geographical data available.\n"

        geo_data_sorted = geo_data.sort_values(by=keyword, ascending=False).head(10)
        for region, row in geo_data_sorted.iterrows():
            report += f"{region} - {row[keyword]}\n"

        report += "\n"
        return report

    def _analyze_seasonality(self, pytrends, keyword, geo):
        pytrends.build_payload([keyword], timeframe='all', geo=geo)
        seasonality_data = pytrends.interest_over_time()
        return seasonality_data

    def _generate_seasonality_report(self, seasonality_data, keyword):
        report = "\nSeasonality Analysis:\n"
        report += "-" * 30 + "\n"

        if seasonality_data.empty:
            return "No seasonality data available.\n"

        report += f"\nSeasonality for '{keyword}':\n"
        max_interest = seasonality_data[keyword].max()
        peak_dates = seasonality_data[seasonality_data[keyword] == max_interest].index

        for date in peak_dates:
            report += f"Peak interest on {date.strftime('%Y-%m-%d')} with value {max_interest}\n"

        report += "\n"
        return report

    def _save_to_txt(self, report, filename):
        self.resource_manager.write_file(filename, report)
        return f"Successfully saved report to {filename}."

    def _save_to_csv(self, data, filename):
        data.to_csv(filename, index=False)
        return f"Successfully saved report to {filename}."

    def _save_to_json(self, data, filename):
        data.to_json(filename, orient='records', date_format='iso')
        return f"Successfully saved data to {filename}."

    def _save_to_db(self, data, table_name):
        engine = create_engine('sqlite:///trends.db')
        data.to_sql(table_name, con=engine, if_exists='replace', index=False)
        return f"Data saved to database table '{table_name}'."
