"""
Менеджер системы NPS опросов с поддержкой групповых чатов
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import desc, func, and_
from app.models.nps_survey import NPSSurvey


class NPSManager:
    def __init__(self, session_maker):
        self.session_maker = session_maker

    def can_user_respond(self, user_id: int, chat_id: int,
                         days_cooldown: int = 7) -> bool:
        """Проверить, может ли пользователь отвечать на NPS (не отвечал последние X дней)"""
        try:
            with self.session_maker() as session:
                cooldown_time = datetime.utcnow() - timedelta(days=days_cooldown)

                recent_response = session.query(NPSSurvey).filter(
                    NPSSurvey.user_id == user_id,
                    NPSSurvey.chat_id == chat_id,
                    NPSSurvey.created_at >= cooldown_time
                ).first()

                return recent_response is None
        except Exception as e:
            print(f"❌ Ошибка проверки cooldown NPS для пользователя {user_id}: {e}")
            return False

    def add_nps_response(self, user_id: int, chat_id: int, score: int,
                         trigger_count: int, message_id: Optional[int] = None,
                         username: Optional[str] = None) -> Optional[int]:
        """Сохранить NPS оценку"""
        if not (0 <= score <= 10):
            return None

        # Дополнительная проверка на дублирование
        if not self.can_user_respond(user_id, chat_id):
            print(f"⚠️ Пользователь {user_id} уже отвечал на NPS в последние 7 дней")
            return None

        try:
            with self.session_maker() as session:
                nps_response = NPSSurvey(
                    user_id=user_id,
                    chat_id=chat_id,
                    username=username,
                    score=score,
                    trigger_count=trigger_count,
                    survey_message_id=message_id
                )
                session.add(nps_response)
                session.commit()
                print(
                    f"✅ Создан NPS ответ #{nps_response.id} - оценка {score} от пользователя {user_id}")
                return nps_response.id
        except Exception as e:
            print(f"❌ Ошибка сохранения NPS: {e}")
            return None

    def get_survey_stats(self, message_id: int) -> Dict[str, Any]:
        """Получить статистику по конкретному опросу"""
        try:
            with self.session_maker() as session:
                responses = session.query(NPSSurvey).filter(
                    NPSSurvey.survey_message_id == message_id
                ).all()

                if not responses:
                    return {"total": 0, "responses": []}

                stats = {
                    "total": len(responses),
                    "average": round(sum(r.score for r in responses) / len(responses)),
                    "promoters": len([r for r in responses if r.score >= 9]),
                    "passives": len([r for r in responses if 7 <= r.score <= 8]),
                    "detractors": len([r for r in responses if r.score <= 6]),
                    "responses": [
                        {"user_id": r.user_id, "username": r.username, "score": r.score}
                        for r in responses]
                }

                # Расчет NPS
                if stats["total"] > 0:
                    stats["nps"] = round(((stats["promoters"] - stats["detractors"]) /
                                          stats["total"]) * 100)
                else:
                    stats["nps"] = 0

                return stats
        except Exception as e:
            print(f"❌ Ошибка получения статистики опроса: {e}")
            return {"total": 0, "responses": []}

    def should_show_nps_for_chat(self, chat_id: int, minutes_cooldown: int = 2880) -> bool:
        """Проверить, нужно ли показывать NPS опрос в чате (не показывался последние X часов)"""
        try:
            with self.session_maker() as session:
                cooldown_time = datetime.utcnow() - timedelta(minutes=minutes_cooldown)

                recent_survey = session.query(NPSSurvey).filter(
                    NPSSurvey.chat_id == chat_id,
                    NPSSurvey.created_at >= cooldown_time
                ).first()

                return recent_survey is None
        except Exception as e:
            print(f"❌ Ошибка проверки cooldown NPS для чата {chat_id}: {e}")
            return False

    def get_nps_stats(self, days: int = 30) -> dict:
        """Общая статистика NPS за N дней"""
        try:
            with self.session_maker() as session:
                start = datetime.utcnow() - timedelta(days=days)
                responses = session.query(NPSSurvey).filter(
                    NPSSurvey.created_at >= start).all()
                total = len(responses)
                promoters = len([r for r in responses if r.score >= 9])
                detractors = len([r for r in responses if r.score <= 6])
                passives = total - promoters - detractors
                nps = round(((promoters - detractors) / total) * 100) if total else 0
                return {
                    "nps_score": nps,
                    "total_responses": total,
                    "promoters": promoters,
                    "passives": passives,
                    "detractors": detractors,
                    "days": days
                }
        except Exception as e:
            print(f"Ошибка: {e}")
            return {"nps_score": 0, "total_responses": 0, "days": days}

    def create_survey_record(self, chat_id: int, message_id: int, trigger_count: int) -> \
    Optional[int]:
        """Создать запись о новом опросе (без оценки)"""
        try:
            with self.session_maker() as session:
                survey = NPSSurvey(
                    user_id=0,  # system
                    chat_id=chat_id,
                    username=None,
                    score=-1,  # отметка «опрос без ответа»
                    trigger_count=trigger_count,
                    survey_message_id=message_id,
                )
                session.add(survey)
                session.commit()
                return survey.id
        except Exception as e:
            print(f"❌ Ошибка создания записи опроса: {e}")
            return None