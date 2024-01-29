from djongo import models

class RealTime(models.Model):
    _id = models.CharField(max_length=255, primary_key=True)
    title = models.CharField(max_length=255)
    url = models.URLField()
    create_time = models.DateTimeField()
    class Meta:
        db_table = 'pymongotest'

class Daily(models.Model):
    rank = models.IntegerField()
    title = models.CharField(max_length=255)
    url = models.URLField()
    create_time = models.DateTimeField()
