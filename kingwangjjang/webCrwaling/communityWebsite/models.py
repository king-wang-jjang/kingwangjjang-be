from djongo import models

from constants import DEFAULT_GPT_ANSWER


class RealTime(models.Model):
    board_id = models.CharField(max_length=255)
    site = models.CharField(max_length=125)
    title = models.CharField(max_length=255)
    url = models.URLField()
    create_time = models.DateTimeField()
    GPTAnswer = models.TextField(default=DEFAULT_GPT_ANSWER)
    
    class Meta:
        db_table = 'realtimebest'
        # unique_together = ['site', 'board_id']

class Daily(models.Model):
    board_id = models.CharField(max_length=255)
    site = models.CharField(max_length=125)
    rank = models.IntegerField()
    title = models.CharField(max_length=255)
    url = models.URLField()
    create_time = models.DateTimeField()
    GPTAnswer = models.TextField(default=DEFAULT_GPT_ANSWER)

    class Meta:
        db_table = 'dailybest'
        # unique_together = ['site', 'board_id']