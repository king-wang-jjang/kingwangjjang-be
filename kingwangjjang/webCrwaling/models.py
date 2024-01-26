from djongo import models

class RealTime(models.Model):
    rank = models.IntegerField()
    title = models.CharField(max_length=255)
    url = models.URLField()
    createTime = models.DateTimeField()

class Daily(models.Model):
    rank = models.IntegerField()
    title = models.CharField(max_length=255)
    url = models.URLField()
    createTime = models.DateTimeField()
