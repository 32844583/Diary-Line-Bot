from django.db import models
 

class Diary(models.Model):
    user_id = models.CharField(max_length=200)  # 使用者ID
    content = models.CharField(max_length=1000)  # 日記
    date = models.DateField()  # 日期
    score = models.FloatField() # 情感分數
    response = models.CharField(max_length=1000, blank=True, null=True)