from datetime import datetime
from extensions import db


class MonitorMysqlSlowQueryReview(db.Model):
    __tablename__ = 'monitor_mysql_slow_query_review'

    checksum = db.Column(db.String(64), primary_key=True)
    sample = db.Column(db.Text, nullable=False)
    last_seen = db.Column(db.DateTime, nullable=False)


class MonitorMysqlSlowQueryReviewHistory(db.Model):
    __tablename__ = 'monitor_mysql_slow_query_review_history'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    checksum = db.Column(db.String(64), nullable=False, index=True)
    resid_max = db.Column(db.BigInteger, nullable=True)
    db_max = db.Column(db.String(100), nullable=True)
    user_max = db.Column(db.String(100), nullable=True)
    ts_cnt = db.Column(db.BigInteger, nullable=False, default=0)
    Query_time_sum = db.Column(db.Float, nullable=False, default=0)
    Query_time_max = db.Column(db.Float, nullable=False, default=0)
    Query_time_min = db.Column(db.Float, nullable=False, default=0)
    ts_min = db.Column(db.DateTime, nullable=False)
    ts_max = db.Column(db.DateTime, nullable=False)


class DbResource(db.Model):
    __tablename__ = 'db_resource'

    res_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    host = db.Column(db.String(100), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    is_delete = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.BigInteger, nullable=False)


class MonitorMysqlSlowQueryOptimized(db.Model):
    __tablename__ = 'monitor_mysql_slow_query_optimized'

    checksum = db.Column(db.String(64), primary_key=True)
    optimized_suggestion = db.Column(db.Text, nullable=True)
    is_optimized = db.Column(db.Integer, nullable=False, default=0)
