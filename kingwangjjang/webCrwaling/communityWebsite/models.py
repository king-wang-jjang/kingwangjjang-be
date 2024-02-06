from djongo import models

class RealTime(models.Model):
    _id = models.CharField(max_length=255, primary_key=True)
    site = models.CharField(max_length=125)
    title = models.CharField(max_length=255)
    url = models.URLField()
    create_time = models.DateTimeField()
    class Meta:
        db_table = 'realtimebest'

class Daily(models.Model):
    rank = models.IntegerField()
    title = models.CharField(max_length=255)
    url = models.URLField()
    create_time = models.DateTimeField()
