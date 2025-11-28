"""
מודול לניהול MongoDB
"""
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.errors import DuplicateKeyError
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from copy import deepcopy
import hashlib
import re
import config

class Database:
    def __init__(self):
        """אתחול חיבור למסד הנתונים"""
        self.client = MongoClient(config.MONGO_URI)
        self.db = self.client[config.MONGO_DB_NAME]
        
        # Collections
        self.prompts = self.db.prompts
        self.users = self.db.users
        self.collections = self.db.collections
        self.stats = self.db.stats
        
        # יצירת אינדקסים
        self._create_indexes()
        # מילוי קודים קצרים למסמכים קיימים (קריאה קלה, בטוחה)
        try:
            self.backfill_short_codes()
        except Exception:
            pass
    
    def _create_indexes(self):
        """יצירת אינדקסים לחיפוש מהיר"""
        # אינדקסים לפרומפטים
        self.prompts.create_index([("user_id", ASCENDING)])
        self.prompts.create_index([("category", ASCENDING)])
        self.prompts.create_index([("tags", ASCENDING)])
        self.prompts.create_index([("created_at", DESCENDING)])
        self.prompts.create_index([("title", TEXT), ("content", TEXT)])
        self.prompts.create_index([("is_deleted", ASCENDING)])
        # קוד קצר ייחודי לכל משתמש; מתעלם ממסמכים ללא short_code תקין
        # נוודא הסרת אינדקס קודם אם נוצר עם אפשרויות שונות
        try:
            self.prompts.drop_index("uniq_short_code_per_user")
        except Exception:
            pass
        self.prompts.create_index(
            [("user_id", ASCENDING), ("short_code", ASCENDING)],
            unique=True,
            name="uniq_short_code_per_user",
            partialFilterExpression={"short_code": {"$type": "string"}}
        )
        
        # אינדקס ייחודי למשתמשים
        self.users.create_index([("user_id", ASCENDING)], unique=True)

    # ====== קטגוריות ברירת מחדל ומסייעים פנימיים ======

    def _default_categories(self) -> List[Dict[str, str]]:
        """החזרת רשימת קטגוריות ברירת מחדל (deepcopy למניעת שיתופים)."""
        return deepcopy([
            {"emoji": emoji, "name": name}
            for emoji, name in config.CATEGORIES.items()
        ])

    @staticmethod
    def _normalize_category_name(name: str) -> str:
        return (name or "").strip()

    @staticmethod
    def _normalize_category_emoji(emoji_value: str) -> str:
        emoji_value = (emoji_value or "").strip()
        # תשמור עד 4 תווים (מספיק גם לאימוג'י עם modifier)
        return emoji_value[:4] if emoji_value else "📁"

    @staticmethod
    def _category_name_key(name: str) -> str:
        return Database._normalize_category_name(name).lower()

    def _fallback_category(self, categories: List[Dict[str, str]], removed: Optional[str] = None) -> Optional[str]:
        """בחירת קטגוריית fallback כאשר קטגוריה מוסרת."""
        if not categories:
            return None
        removed_key = self._category_name_key(removed) if removed else None
        # עדיפות ל-"Other" אם קיים
        for cat in categories:
            if self._category_name_key(cat.get("name")) == "other" and self._category_name_key(cat.get("name")) != removed_key:
                return cat.get("name")
        # אחרת החזר את הראשונה שאינה הקטגוריה שהוסרה
        for cat in categories:
            if self._category_name_key(cat.get("name")) != removed_key:
                return cat.get("name")
        return None
    
    # ========== פעולות משתמשים ==========
    
    def get_or_create_user(self, user_id: int, username: str = None, 
                          first_name: str = None) -> Dict:
        """קבלת או יצירת משתמש"""
        user = self.users.find_one({"user_id": user_id})
        
        if not user:
            user = {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "created_at": datetime.utcnow(),
                "settings": {
                    "show_ids": False,
                    "short_titles": True,
                    "show_tags": True,
                    "copy_confirmation": True,
                    "theme": "dark"
                },
                "stats": {
                    "total_prompts": 0,
                    "total_uses": 0,
                    "total_collections": 0
                },
                "categories": self._default_categories()
            }
            self.users.insert_one(user)
        elif not user.get("categories"):
            categories = self._default_categories()
            self.users.update_one(
                {"user_id": user_id},
                {"$set": {"categories": categories}}
            )
            user["categories"] = categories
        
        return user
    
    def update_user_stats(self, user_id: int, stat_name: str, increment: int = 1):
        """עדכון סטטיסטיקות משתמש"""
        self.users.update_one(
            {"user_id": user_id},
            {"$inc": {f"stats.{stat_name}": increment}}
        )
    
    # ========== קטגוריות משתמש ==========

    def get_user_categories(self, user_id: int) -> List[Dict[str, str]]:
        """החזרת רשימת הקטגוריות של משתמש (יוזנו ברירות מחדל אם חסרות)."""
        user = self.users.find_one({"user_id": user_id}, {"categories": 1})
        categories = (user or {}).get("categories")
        if not categories:
            categories = self._default_categories()
            self.users.update_one(
                {"user_id": user_id},
                {"$set": {"categories": categories}},
                upsert=True
            )
        return deepcopy(categories)

    def get_category_lookup(self, user_id: int) -> Dict[str, str]:
        """מילון מהיר של שם קטגוריה -> אימוג׳י."""
        return {
            cat.get("name"): cat.get("emoji", "📁")
            for cat in self.get_user_categories(user_id)
        }

    def get_category(self, user_id: int, name: str) -> Optional[Dict[str, str]]:
        """החזרת אובייקט קטגוריה לפי שם (case-insensitive)."""
        categories = self.get_user_categories(user_id)
        normalized = self._category_name_key(name or "")
        for cat in categories:
            if self._category_name_key(cat.get("name")) == normalized:
                return cat
        return None

    def ensure_category_name(self, user_id: int, category: Optional[str]) -> str:
        """ודאות שהקטגוריה קיימת; אם לא – חזרה לברירת מחדל."""
        categories = self.get_user_categories(user_id)
        normalized = self._category_name_key(category or "")
        for cat in categories:
            if self._category_name_key(cat.get("name")) == normalized:
                return cat.get("name")
        fallback = self._fallback_category(categories)
        return fallback or "Other"

    def add_user_category(self, user_id: int, name: str, emoji: str = "📁") -> bool:
        name = self._normalize_category_name(name)
        if len(name) < 2 or len(name) > 40:
            raise ValueError("שם הקטגוריה חייב להיות בין 2 ל-40 תווים.")
        emoji = self._normalize_category_emoji(emoji)
        categories = self.get_user_categories(user_id)
        key = self._category_name_key(name)
        if any(self._category_name_key(cat.get("name")) == key for cat in categories):
            raise ValueError("קטגוריה בשם זה כבר קיימת.")
        categories.append({"emoji": emoji, "name": name})
        self.users.update_one(
            {"user_id": user_id},
            {"$set": {"categories": categories}}
        )
        return True

    def update_user_category(self, user_id: int, old_name: str, new_name: str, emoji: str) -> bool:
        new_name = self._normalize_category_name(new_name)
        if len(new_name) < 2 or len(new_name) > 40:
            raise ValueError("שם הקטגוריה חייב להיות בין 2 ל-40 תווים.")
        emoji = self._normalize_category_emoji(emoji)
        categories = self.get_user_categories(user_id)
        old_key = self._category_name_key(old_name)
        target = None
        stored_old_name = None
        for cat in categories:
            if self._category_name_key(cat.get("name")) == old_key:
                target = cat
                stored_old_name = cat.get("name")
                break
        if not target:
            raise ValueError("הקטגוריה המבוקשת לא נמצאה.")
        new_key = self._category_name_key(new_name)
        if new_key != old_key and any(self._category_name_key(cat.get("name")) == new_key for cat in categories):
            raise ValueError("קטגוריה בשם זה כבר קיימת.")
        target["name"] = new_name
        target["emoji"] = emoji
        self.users.update_one(
            {"user_id": user_id},
            {"$set": {"categories": categories}}
        )
        if new_key != old_key and stored_old_name:
            self.prompts.update_many(
                {"user_id": user_id, "category": stored_old_name},
                {"$set": {"category": new_name}}
            )
        return True

    def delete_user_category(self, user_id: int, name: str) -> str:
        categories = self.get_user_categories(user_id)
        if len(categories) <= 1:
            raise ValueError("יש להשאיר לפחות קטגוריה אחת.")
        key = self._category_name_key(name)
        target_name = None
        filtered = []
        for cat in categories:
            if self._category_name_key(cat.get("name")) == key:
                target_name = cat.get("name")
                continue
            filtered.append(cat)
        if target_name is None:
            raise ValueError("הקטגוריה המבוקשת לא נמצאה.")
        fallback = self._fallback_category(filtered, removed=target_name)
        if not fallback:
            raise ValueError("אין קטגוריית fallback זמינה.")
        # עדכון פרומפטים לקטגוריית fallback
        self.prompts.update_many(
            {"user_id": user_id, "category": target_name},
            {"$set": {"category": fallback}}
        )
        self.users.update_one(
            {"user_id": user_id},
            {"$set": {"categories": filtered}}
        )
        return fallback

    # ========== פעולות פרומפטים ==========
    
    def save_prompt(self, user_id: int, content: str, title: str = None,
                   category: str = "Other", tags: List[str] = None) -> Dict:
        """שמירת פרומפט חדש"""
        category = self.ensure_category_name(user_id, category)
        prompt = {
            "user_id": user_id,
            "content": content,
            "title": title or content[:50] + "..." if len(content) > 50 else content,
            "category": category,
            "tags": tags or [],
            "is_favorite": False,
            "is_deleted": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "use_count": 0,
            "length": len(content)
        }
        
        result = self.prompts.insert_one(prompt)
        prompt['_id'] = result.inserted_id
        
        # קוד קצר דטרמיניסטי על בסיס ה-ID, עם טיפול בהתנגשויות
        try:
            short_code = self._ensure_short_code_for(str(prompt['_id']), user_id)
            if short_code:
                prompt['short_code'] = short_code
        except Exception:
            # לא נכשיל שמירה בגלל קוד קצר
            pass
        
        # עדכון סטטיסטיקות
        self.update_user_stats(user_id, "total_prompts")
        
        return prompt
    
    def get_prompt(self, prompt_id: str, user_id: int) -> Optional[Dict]:
        """קבלת פרומפט לפי מזהה או קוד קצר (דטרמיניסטי)."""
        from bson import ObjectId
        # ניסיון לפי ObjectId
        if isinstance(prompt_id, str) and re.fullmatch(r"[0-9a-fA-F]{24}", prompt_id or ""):
            try:
                return self.prompts.find_one({
                    "_id": ObjectId(prompt_id),
                    "user_id": user_id,
                    "is_deleted": False
                })
            except Exception:
                pass
        # ניסיון לפי short_code (4-8 תווים הקסה, לא תלוי רישיות)
        code = (prompt_id or "").strip().upper()
        if re.fullmatch(r"[0-9A-F]{4,8}", code):
            return self.prompts.find_one({
                "short_code": code,
                "user_id": user_id,
                "is_deleted": False
            })
        return None

    # ====== קוד קצר ======
    def _generate_short_code(self, prompt_id: str, length: int = 4) -> str:
        digest = hashlib.md5(str(prompt_id).encode()).hexdigest().upper()
        return digest[:max(4, min(length, 12))]

    def _ensure_short_code_for(self, prompt_id: str, user_id: int) -> Optional[str]:
        """מקצה שדה short_code למסמך לפי prompt_id, עם טיפול בהתנגשויות.
        מחזיר את הקוד שהוקצה או None אם נכשל בלי להחריג.
        """
        # ננסה להאריך עד 8 תווים במקרה התנגשות (נדיר מאוד)
        for length in range(4, 9):
            code = self._generate_short_code(prompt_id, length)
            try:
                # בדיקת קיום
                existing = self.prompts.find_one({"user_id": user_id, "short_code": code})
                if existing and str(existing.get("_id")) != str(prompt_id):
                    continue  # התנגשות, ננסה אורך ארוך יותר
                # עדכון השדה במסמך הנוכחי
                from bson import ObjectId
                self.prompts.update_one(
                    {"_id": ObjectId(prompt_id), "user_id": user_id},
                    {"$set": {"short_code": code}}
                )
                return code
            except DuplicateKeyError:
                continue
            except Exception:
                # לא נעצור את הזרימה
                break
        return None

    def backfill_short_codes(self):
        """מילוי לאחור של short_code למסמכים חסרי שדה זה או עם ערך לא תקין."""
        cursor = self.prompts.find({
            "$or": [
                {"short_code": {"$exists": False}},
                {"short_code": None},
                {"short_code": ""}
            ]
        })
        for doc in cursor:
            user_id = doc.get("user_id")
            _id = str(doc.get("_id"))
            try:
                self._ensure_short_code_for(_id, user_id)
            except Exception:
                continue
    
    def update_prompt(self, prompt_id: str, user_id: int, 
                     update_data: Dict) -> bool:
        """עדכון פרומפט"""
        from bson import ObjectId
        try:
            update_data['updated_at'] = datetime.utcnow()
            result = self.prompts.update_one(
                {"_id": ObjectId(prompt_id), "user_id": user_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except:
            return False
    
    def delete_prompt(self, prompt_id: str, user_id: int, 
                     permanent: bool = False) -> bool:
        """מחיקת פרומפט (רכה או קשה)"""
        from bson import ObjectId
        try:
            if permanent:
                result = self.prompts.delete_one({
                    "_id": ObjectId(prompt_id),
                    "user_id": user_id
                })
            else:
                result = self.prompts.update_one(
                    {"_id": ObjectId(prompt_id), "user_id": user_id},
                    {"$set": {
                        "is_deleted": True,
                        "deleted_at": datetime.utcnow()
                    }}
                )
            
            if result.modified_count > 0 or result.deleted_count > 0:
                self.update_user_stats(user_id, "total_prompts", -1)
                return True
            return False
        except:
            return False
    
    def restore_prompt(self, prompt_id: str, user_id: int) -> bool:
        """שחזור פרומפט מהאשפה"""
        from bson import ObjectId
        try:
            result = self.prompts.update_one(
                {"_id": ObjectId(prompt_id), "user_id": user_id},
                {"$set": {"is_deleted": False}, "$unset": {"deleted_at": ""}}
            )
            if result.modified_count > 0:
                self.update_user_stats(user_id, "total_prompts", 1)
                return True
            return False
        except:
            return False
    
    def increment_use_count(self, prompt_id: str, user_id: int):
        """הגדלת מונה שימושים"""
        from bson import ObjectId
        try:
            self.prompts.update_one(
                {"_id": ObjectId(prompt_id), "user_id": user_id},
                {"$inc": {"use_count": 1}}
            )
            self.update_user_stats(user_id, "total_uses")
        except:
            pass
    
    # ========== חיפוש וסינון ==========
    
    def search_prompts(self, user_id: int, query: str = None, 
                      category: str = None, tags: List[str] = None,
                      favorites_only: bool = False, 
                      skip: int = 0, limit: int = 10) -> List[Dict]:
        """חיפוש פרומפטים עם סינון"""
        filter_query = {
            "user_id": user_id,
            "is_deleted": False
        }
        
        # חיפוש טקסט
        if query:
            filter_query["$text"] = {"$search": query}
        
        # סינון לפי קטגוריה
        if category:
            filter_query["category"] = category
        
        # סינון לפי תגיות
        if tags:
            filter_query["tags"] = {"$in": tags}
        
        # מועדפים בלבד
        if favorites_only:
            filter_query["is_favorite"] = True
        
        # ביצוע החיפוש
        prompts = list(self.prompts.find(filter_query)
                      .sort("created_at", DESCENDING)
                      .skip(skip)
                      .limit(limit))
        
        return prompts
    
    def get_all_prompts(self, user_id: int, skip: int = 0, 
                       limit: int = 10) -> List[Dict]:
        """קבלת כל הפרומפטים של משתמש"""
        return list(self.prompts.find({
            "user_id": user_id,
            "is_deleted": False
        }).sort("created_at", DESCENDING).skip(skip).limit(limit))
    
    def get_favorites(self, user_id: int) -> List[Dict]:
        """קבלת פרומפטים מועדפים"""
        return list(self.prompts.find({
            "user_id": user_id,
            "is_favorite": True,
            "is_deleted": False
        }).sort("use_count", DESCENDING))
    
    def get_trash(self, user_id: int) -> List[Dict]:
        """קבלת פרומפטים באשפה"""
        return list(self.prompts.find({
            "user_id": user_id,
            "is_deleted": True
        }).sort("deleted_at", DESCENDING))
    
    def get_popular_prompts(self, user_id: int, limit: int = 10) -> List[Dict]:
        """קבלת הפרומפטים הפופולריים ביותר"""
        return list(self.prompts.find({
            "user_id": user_id,
            "is_deleted": False
        }).sort("use_count", DESCENDING).limit(limit))
    
    def count_prompts(self, user_id: int, **filters) -> int:
        """ספירת פרומפטים"""
        filter_query = {"user_id": user_id, "is_deleted": False}
        filter_query.update(filters)
        return self.prompts.count_documents(filter_query)
    
    # ========== תגיות ==========
    
    def get_all_tags(self, user_id: int) -> List[str]:
        """קבלת כל התגיות של משתמש"""
        pipeline = [
            {"$match": {"user_id": user_id, "is_deleted": False}},
            {"$unwind": "$tags"},
            {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        results = list(self.prompts.aggregate(pipeline))
        return [r['_id'] for r in results]
    
    # ========== סטטיסטיקות ==========
    
    def get_user_statistics(self, user_id: int) -> Dict:
        """קבלת סטטיסטיקות מפורטות"""
        user = self.users.find_one({"user_id": user_id})
        
        # קטגוריות פופולריות
        category_stats = list(self.prompts.aggregate([
            {"$match": {"user_id": user_id, "is_deleted": False}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ]))
        
        # תגיות פופולריות
        tag_stats = list(self.prompts.aggregate([
            {"$match": {"user_id": user_id, "is_deleted": False}},
            {"$unwind": "$tags"},
            {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ]))
        
        return {
            "user": user.get('stats', {}),
            "categories": category_stats,
            "tags": tag_stats
        }

    def get_admin_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        החזרת נתוני סטטיסטיקה גלובליים למנהל.

        מספר משתמשים חדשים ב-X הימים האחרונים + מספר פעולות (שמירות + שימושים)
        לכל משתמש.
        """
        since = datetime.utcnow() - timedelta(days=days)
        recent_users = self.users.count_documents({
            "created_at": {"$gte": since}
        })
        total_users = self.users.count_documents({})

        user_actions: List[Dict[str, Any]] = []
        cursor = self.users.find(
            {},
            {
                "user_id": 1,
                "username": 1,
                "first_name": 1,
                "stats": 1
            }
        )
        for doc in cursor:
            stats = doc.get("stats") or {}
            total_prompts = int(stats.get("total_prompts") or 0)
            total_uses = int(stats.get("total_uses") or 0)
            action_count = total_prompts + total_uses
            user_actions.append({
                "user_id": doc.get("user_id"),
                "username": doc.get("username"),
                "first_name": doc.get("first_name"),
                "total_prompts": total_prompts,
                "total_uses": total_uses,
                "action_count": action_count
            })

        user_actions.sort(key=lambda item: (item["action_count"], item["total_uses"]), reverse=True)

        return {
            "recent_users": recent_users,
            "total_users": total_users,
            "user_actions": user_actions
        }
    
    # ========== ניקוי ==========
    
    def cleanup_old_trash(self):
        """מחיקה סופית של פרומפטים ישנים באשפה"""
        threshold = datetime.utcnow() - timedelta(days=config.TRASH_RETENTION_DAYS)
        result = self.prompts.delete_many({
            "is_deleted": True,
            "deleted_at": {"$lt": threshold}
        })
        return result.deleted_count

# יצירת instance גלובלי
db = Database()
