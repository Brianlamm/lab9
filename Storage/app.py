import connexion
from connexion import NoContent
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from base import Base
from sale import Sale
from ticket import Ticket
import pymysql
import datetime
import yaml
import logging
import logging.config
import json 
from pykafka import KafkaClient  
from pykafka.common import OffsetType  
from threading import Thread 

with open('app_conf.yml', 'r') as f: 
    app_config = yaml.safe_load(f.read())

with open('log_conf.yml', 'r') as f: 
    log_config = yaml.safe_load(f.read()) 
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')

DB_ENGINE = create_engine('mysql+pymysql://%s:%s@%s:%s/%s' % (app_config['datastore']['user'],app_config['datastore']['password'],app_config['datastore']['hostname'],app_config['datastore']['port'],app_config['datastore']['db']))

Base.metadata.bind = DB_ENGINE
DB_SESSION = sessionmaker(bind=DB_ENGINE)

logger.info(f'Connecting to DB. Hostname: {app_config["datastore"]["hostname"]}, Port: {app_config["datastore"]["port"]}')

# def report_ticket_info(body): 
    
#     session = DB_SESSION()

#     ticket = Ticket(body['ticket_id'],
#                        body['date'],
#                        body['team1'],
#                        body['team2'],
#                        body['seat_number'],
#                        body['trace_id'])

#     session.add(ticket)

#     session.commit()
#     session.close()

#     logging.debug(f'Stored event ticket request with a trace id of {body["trace_id"]}')
#     return NoContent, 201 

def get_report_ticket_info(timestamp): 
    """ Gets new ticket reports after the timestamp """ 
 
    session = DB_SESSION() 
 
    timestamp_datetime = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ") 
   
 
    reports = session.query(Ticket).filter(Ticket.date_created >= timestamp_datetime) 
 
    results_list = [] 
 
    for report in reports: 
        results_list.append(report.to_dict()) 
 
    session.close() 
     
    logger.info("Query for Ticket report after %s returns %d results" %  
                (timestamp, len(results_list))) 
 
    return results_list, 200


# def report_sale_info(body): 

#     session = DB_SESSION()

#     sale = Sale(body['sale_id'],
#                    body['price'],
#                    body['quantity'],
#                    body['trace_id'])

#     session.add(sale)

#     session.commit()
#     session.close()

#     logging.debug(f'Stored event sale request with a trace id of {body["trace_id"]}')

#     return NoContent, 201

def get_report_sale_info(timestamp): 
    """ Gets new sale reports after the timestamp """ 
 
    session = DB_SESSION() 
 
    timestamp_datetime = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ") 
   
 
    reports = session.query(Sale).filter(Sale.date_created >= timestamp_datetime) 
 
    results_list = [] 
 
    for report in reports: 
        results_list.append(report.to_dict()) 
 
    session.close() 
     
    logger.info("Query for Sale report after %s returns %d results" %  
                (timestamp, len(results_list))) 
 
    return results_list, 200

def process_messages(): 
    """ Process event messages """ 
    hostname = "%s:%d" % (app_config["events"]["hostname"],   
                          app_config["events"]["port"]) 
    client = KafkaClient(hosts=hostname) 
    topic = client.topics[str.encode(app_config["events"]["topic"])] 
     
    # Create a consume on a consumer group, that only reads new messages  
    # (uncommitted messages) when the service re-starts (i.e., it doesn't  
    # read all the old messages from the history in the message queue). 
    consumer = topic.get_simple_consumer(consumer_group=b'event_group', 
                                         reset_offset_on_start=False, 
                                         auto_offset_reset=OffsetType.LATEST) 
 
    # This is blocking - it will wait for a new message 
    for msg in consumer: 
        msg_str = msg.value.decode('utf-8') 
        msg = json.loads(msg_str) 
        logger.info("Message: %s" % msg) 
 
        payload = msg["payload"] 
 
        if msg["type"] == "ticket": # Change this to your event type 
            # Store the event1 (i.e., the payload) to the DB 
            session = DB_SESSION()

            ticket = Ticket(payload['ticket_id'],
                            payload['date'],
                            payload['team1'],
                            payload['team2'],
                            payload['seat_number'],
                            payload['trace_id'])

            session.add(ticket)

            session.commit()
            session.close()
        elif msg["type"] == "sale": # Change this to your event type 
            # Store the event2 (i.e., the payload) to the DB 
            session = DB_SESSION()

            sale = Sale(payload['sale_id'],
                        payload['price'],
                        payload['quantity'],
                        payload['trace_id'])

            session.add(sale)

            session.commit()
            session.close()
        # Commit the new message as being read 
        consumer.commit_offsets() 

app = connexion.FlaskApp(__name__, specification_dir='') 
app.add_api("openapi.yml",
strict_validation=True,  
validate_responses=True) 
 
if __name__ == "__main__": 
    t1 = Thread(target=process_messages) 
    t1.setDaemon(True) 
    t1.start()
    app.run(port=8090)