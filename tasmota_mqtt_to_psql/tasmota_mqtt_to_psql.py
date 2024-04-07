import argparse
import json
import logging

import paho.mqtt.client as mqtt
import psycopg


# TODO reduce write on database to reduce wear on ssd; write once every 5 minutes?
# TODO graceful shutdown: catch CTRL+C
# ~TODO move topic to extra table to reduce size~ it does not make that much of a difference so let it be for the moment


class MqttToTimescaledb:
    def __init__(self, db_connection_string, mqtt_host, mqtt_port, mqtt_client_id):
        # https://www.psycopg.org/psycopg3/docs/basic/usage.html
        # https://www.psycopg.org/psycopg3/docs/basic/params.html
        self.sql_conn = psycopg.connect(conninfo=db_connection_string)
        self.sql_conn.commit()

        # https://pypi.org/project/paho-mqtt/
        # https://github.com/aschiffler/python-mqtt/blob/main/index.ipynb
        self.mqtt_client = mqtt.Client(client_id=mqtt_client_id, clean_session=False, userdata=None)

        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.message_callback_add("tele/#", self._on_tele_sensor)

        self.mqtt_client.connect(mqtt_host, mqtt_port, 60)

        try:
            self.mqtt_client.loop_forever()
        except KeyboardInterrupt:
            self.mqtt_client.disconnect()

    def _on_connect(self, client, userdata, flags, rc):
        logging.debug("Connected with result code " + str(rc))
        self.mqtt_client.subscribe("tele/#")

    def _write_sql(self, database_name, data):
        logging.debug(f"Writing to {database_name}: {data}")

        statement = psycopg.sql.SQL("INSERT INTO {}({}) VALUES({})").format(
            psycopg.sql.Identifier(database_name),
            psycopg.sql.SQL(", ").join(map(psycopg.sql.Identifier, data.keys())),
            psycopg.sql.SQL(", ").join(map(psycopg.sql.Placeholder, data.keys())),
        )

        try:
            self.sql_conn.execute(statement, data)
            self.sql_conn.commit()

        except Exception as e:
            self.sql_conn.rollback()
            logging.exception(e)

    def _on_tele_sensor(self, client, userdata, message):
        if message.topic.endswith("/LWT"):
            # Ignore Last Will and Testament
            return

        payload = json.loads(message.payload)
        logging.debug(f"{message.topic}: {message.payload}")

        if message.topic.endswith("/STATE"):
            self._write_sql(
                "tasmota_state",
                {
                    "time": payload.get("Time"),
                    "topic": message.topic,
                    "load_avg": payload.get("LoadAvg"),
                    "wifi_rssi": payload.get("Wifi").get("RSSI"),
                    "wifi_signal": payload.get("Wifi").get("Signal"),
                    "wifi_link_count": payload.get("Wifi").get("LinkCount"),
                },
            )

        if payload.get("ENERGY"):
            self._write_sql(
                "tasmota_energy",
                {
                    "time": payload.get("Time"),
                    "topic": message.topic,
                    "total": payload.get("ENERGY").get("Total"),
                    "power": payload.get("ENERGY").get("Power"),
                    "apparent_power": payload.get("ENERGY").get("ApparentPower"),
                    "reactive_power": payload.get("ENERGY").get("ReactivePower"),
                    "factor": payload.get("ENERGY").get("Factor"),
                    "voltage": payload.get("ENERGY").get("Voltage"),
                    "current": payload.get("ENERGY").get("Current"),
                },
            )

        if payload.get("BME280"):
            self._write_sql(
                "tasmota_bme280",
                {
                    "time": payload.get("Time"),
                    "topic": message.topic,
                    "dew_point": payload.get("BME280").get("DewPoint"),
                    "humidity": payload.get("BME280").get("Humidity"),
                    "pressure": payload.get("BME280").get("Pressure"),
                    "temperature": payload.get("BME280").get("Temperature"),
                },
            )

        if payload.get("PMS7003"):
            self._write_sql("tasmota_pms7003", {"time": payload.get("Time"), "topic": message.topic} | payload.get("PMS7003"))

        if payload.get("SDS0X1"):
            self._write_sql(
                "tasmota_sds0x1",
                {
                    "time": payload.get("Time"),
                    "topic": message.topic,
                    "pm2_5": payload.get("SDS0X1").get("PM2.5"),
                    "pm10": payload.get("SDS0X1").get("PM10"),
                },
            )

        if payload.get("ANALOG"):
            self._write_sql(
                "tasmota_analog",
                {
                    "time": payload.get("Time"),
                    "topic": message.topic,
                    "analog": payload.get("ANALOG").get("A0"),
                },
            )

        # the Hichi sensor53 has **no** key for the payload data so we need to check based on payload key names to make it unique
        # would be worse having data in the wrong table instead of no data
        if all(
            i in payload.get("", {}).keys()
            for i in [
                "total",
                "tariff_1",
                "tariff_2",
                "neg_total",
                "neg_tariff_1",
                "neg_tariff_2",
                "current",
            ]
        ):
            self._write_sql(
                "tasmota_hichi",
                {
                    "time": payload.get("Time"),
                    "topic": message.topic,
                    "total": payload.get("").get("total"),
                    "tariff_1": payload.get("").get("tariff_1"),
                    "tariff_2": payload.get("").get("tariff_2"),
                    "neg_total": payload.get("").get("neg_total"),
                    "neg_tariff_1": payload.get("").get("neg_tariff_1"),
                    "neg_tariff_2": payload.get("").get("neg_tariff_2"),
                    "current": payload.get("").get("current"),
                },
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--db_connection_string", required=True)
    parser.add_argument("--mqtt_host", required=True)
    parser.add_argument("--mqtt_port", default=1883)
    parser.add_argument("--mqtt_client_id", default="tasmota_mqtt_to_psql")
    parser.add_argument("--log", default=logging.ERROR)

    args = parser.parse_args()

    logging.basicConfig(level=args.log)

    MqttToTimescaledb(args.db_connection_string, args.mqtt_host, args.mqtt_port, args.mqtt_client_id)
