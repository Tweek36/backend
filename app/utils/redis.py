import hashlib
from uuid import UUID, uuid4
from aioredis import Redis
import inspect
from functools import wraps
import json
import asyncio
from typing import Callable, Any
from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase
from app.database import get_redis


async def generate_unique_redis_key(redis: Redis, prefix: str = "key") -> str:
    while True:
        new_key = f"{prefix}:{uuid4()}"
        exists = await redis.exists(new_key)
        if not exists:
            return new_key


def calculate_hash(args: tuple, kwargs: dict):
    # Если func - метод класса, исключаем self (первый аргумент)
    if args and hasattr(args[0], '__class__'):
        args = args[1:]  # Исключаем self
    
    # Преобразуем kwargs в отсортированный список для гарантированной последовательности
    kwargs_tuple = tuple(sorted(kwargs.items()))
    
    # Комбинируем args и kwargs
    arg_tuple = args + kwargs_tuple
    
    # Создаем хэш
    hash_value = hashlib.md5(str(arg_tuple).encode()).hexdigest()
    return hash_value


def model_to_dict(model) -> dict:
    return {column.name: getattr(model, column.name) for column in model.__table__.columns}


def recursive_convert(obj):
    if isinstance(obj, DeclarativeBase):
        return {key: recursive_convert(value) for key, value in model_to_dict(obj).items()}
    
    if isinstance(obj, BaseModel):
        return {key: recursive_convert(value) for key, value in obj.model_dump().items()}
    
    if isinstance(obj, (list, tuple)):
        return [recursive_convert(item) for item in obj]
    
    if isinstance(obj, dict):
        return {key: recursive_convert(value) for key, value in obj.items()}
    
    return obj

def resolve_annotation(anatation: Any, obj: Any):
    if hasattr(anatation, "__origin__"):
        origin = anatation.__origin__

        if origin is dict:
            return {k: resolve_annotation(anatation.__args__[1], v) for k, v in obj.items()}
        
        if origin in (list, tuple):
            return [resolve_annotation(anatation.__args__[0], i) for i in obj]
        
        return obj
    
    if isinstance(obj, dict):
        return anatation(**obj)
    
    return anatation(obj)

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


def cache(expire: int = 3600):

    def decorator(func: Callable) -> Callable:
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            redis = next(get_redis())
            cache_key = f"cache:{func.__qualname__}:{calculate_hash(args, kwargs)}"

            cached_result = await redis.get(cache_key)
            if cached_result:
                res = resolve_annotation(func.__annotations__.get("return"), json.loads(cached_result))
                return res

            result = await func(*args, **kwargs)
            await redis.setex(cache_key, expire, json.dumps(recursive_convert(result), cls=CustomJSONEncoder))
            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            redis = next(get_redis())
            cache_key = f"cache:{func.__qualname__}:{calculate_hash(args, kwargs)}"

            async def async_cache_operations():
                cached_result = await redis.get(cache_key)
                if cached_result:
                    return resolve_annotation(func.__annotations__.get("return"), json.loads(cached_result))
                
                result = func(*args, **kwargs)
                await redis.setex(cache_key, expire, json.dumps(recursive_convert(result)))
                return result

            return asyncio.run(async_cache_operations())

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator

async def delete_function_cache(func: Callable):
    redis = next(get_redis())
    pattern = f"cache:{func.__qualname__}:*"
    cursor = b'0'
    while cursor:
        cursor, keys = await redis.scan(cursor=cursor, match=pattern)
        if keys:
            await redis.delete(*keys)
    