from app.services import BaseService, ModelRequests
from app.models.tests import RatingChoice


class RatingChoiceService(BaseService, ModelRequests[RatingChoice]):
    model = RatingChoice
