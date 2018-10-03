from . import manager
from APITaxi_models import db

@manager.command
def remove_old_ads():
    if not db.session.execute("SELECT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'ADS_old')").fetchone()[0]:
        db.session.execute("""
           CREATE TABLE "ADS_old" AS TABLE "ADS" WITH NO DATA;
        """)
    db.session.execute("""
        INSERT INTO "ADS_old"
        SELECT * FROM "ADS" 
        WHERE "ADS".id NOT IN (SELECT ads_id FROM taxi)
        AND "ADS".id NOT IN (SELECT id FROM "ADS_old")
    """)
    db.session.execute("""
        DELETE FROM "ADS" where id IN (SELECT id FROM "ADS_old")
    """)
    db.session.commit()

@manager.command
def restore_old_ads():
    db.session.execute(""" 
        INSERT INTO "ADS" SELECT * FROM "ADS_old"
    """)
    db.session.commit()
