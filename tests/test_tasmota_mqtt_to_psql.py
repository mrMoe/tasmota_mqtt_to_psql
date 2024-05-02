# https://realpython.com/pytest-python-testing/
# https://realpython.com/python-mock-library/
import paho.mqtt.publish as publish
import psycopg
import pytest
from psycopg.sql import SQL, Composed, Identifier, Placeholder

from tasmota_mqtt_to_psql.tasmota_mqtt_to_psql import MqttToTimescaledb


def test_sql_write(mocker):
    psycopg_mock = mocker.patch("tasmota_mqtt_to_psql.tasmota_mqtt_to_psql.psycopg.connect")
    mocker.patch("tasmota_mqtt_to_psql.tasmota_mqtt_to_psql.mqtt")

    sut = MqttToTimescaledb("", "", "", "")

    sut._write_sql(
        "tasmota_energy",
        {
            "time": "2023-05-19T20:52:56",
            "topic": "tele/sonoff_desk/SENSOR",
            "total": 514.153,
            "power": 56,
            "apparent_power": 92,
            "reactive_power": 73,
            "factor": 0.61,
            "voltage": 234,
            "current": 0.392,
        },
    )

    psycopg_mock.return_value.execute.assert_called_with(
        Composed(
            [
                SQL("INSERT INTO "),
                Identifier("tasmota_energy"),
                SQL("("),
                Composed(
                    [
                        Identifier("time"),
                        SQL(", "),
                        Identifier("topic"),
                        SQL(", "),
                        Identifier("total"),
                        SQL(", "),
                        Identifier("power"),
                        SQL(", "),
                        Identifier("apparent_power"),
                        SQL(", "),
                        Identifier("reactive_power"),
                        SQL(", "),
                        Identifier("factor"),
                        SQL(", "),
                        Identifier("voltage"),
                        SQL(", "),
                        Identifier("current"),
                    ]
                ),
                SQL(") VALUES("),
                Composed(
                    [
                        Placeholder("time"),
                        SQL(", "),
                        Placeholder("topic"),
                        SQL(", "),
                        Placeholder("total"),
                        SQL(", "),
                        Placeholder("power"),
                        SQL(", "),
                        Placeholder("apparent_power"),
                        SQL(", "),
                        Placeholder("reactive_power"),
                        SQL(", "),
                        Placeholder("factor"),
                        SQL(", "),
                        Placeholder("voltage"),
                        SQL(", "),
                        Placeholder("current"),
                    ]
                ),
                SQL(")"),
            ]
        ),
        {
            "time": "2023-05-19T20:52:56",
            "topic": "tele/sonoff_desk/SENSOR",
            "total": 514.153,
            "power": 56,
            "apparent_power": 92,
            "reactive_power": 73,
            "factor": 0.61,
            "voltage": 234,
            "current": 0.392,
        },
    )


@pytest.fixture
def write_sql_mock(mocker):
    return mocker.patch("tasmota_mqtt_to_psql.tasmota_mqtt_to_psql.MqttToTimescaledb._write_sql")


@pytest.fixture
def sensor_sut(mocker):
    mocker.patch("tasmota_mqtt_to_psql.tasmota_mqtt_to_psql.psycopg")
    mocker.patch("tasmota_mqtt_to_psql.tasmota_mqtt_to_psql.mqtt")

    return MqttToTimescaledb("", "", "", "")


def test_tele_state(sensor_sut, write_sql_mock, mocker):
    sensor_sut._on_tele_sensor(
        "",
        {},
        mocker.Mock(
            topic="tele/sonoff-desk/STATE",
            payload='{"Time":"2022-11-06T21:27:46","Uptime":"13T23:45:18","UptimeSec":1208718,"Heap":25,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"MqttCount":19,"POWER":"ON","Wifi":{"AP":1,"SSId":"dreamworks_vlan_55_iot","BSSId":"F4:92:BF:8B:40:34","Channel":6,"Mode":"11n","RSSI":56,"Signal":-72,"LinkCount":14,"Downtime":"0T00:06:24"}}',
        ),
    )

    write_sql_mock.assert_called_with(
        "tasmota_state",
        {
            "time": "2022-11-06T21:27:46",
            "topic": "tele/sonoff-desk/STATE",
            "load_avg": 19,
            "wifi_rssi": 56,
            "wifi_signal": -72,
            "wifi_link_count": 14,
        },
    )


def test_energy_sensor(sensor_sut, write_sql_mock, mocker):
    sensor_sut._on_tele_sensor(
        "",
        {},
        mocker.Mock(
            topic="tele/sonoff_desk/SENSOR",
            payload='{"Time":"2023-05-19T20:52:56","ENERGY":{"TotalStartTime":"2022-03-20T15:20:48","Total":514.153,"Yesterday":1.495,"Today":0.537,"Period":0,"Power":56,"ApparentPower":92,"ReactivePower":73,"Factor":0.61,"Voltage":234,"Current":0.392}}',
        ),
    )

    write_sql_mock.assert_called_with(
        "tasmota_energy",
        {
            "time": "2023-05-19T20:52:56",
            "topic": "tele/sonoff_desk/SENSOR",
            "total": 514.153,
            "power": 56,
            "apparent_power": 92,
            "reactive_power": 73,
            "factor": 0.61,
            "voltage": 234,
            "current": 0.392,
        },
    )


def test_bm3280_sensor(sensor_sut, write_sql_mock, mocker):
    sensor_sut._on_tele_sensor(
        "",
        {},
        mocker.Mock(
            topic="tele/node_mcu_hydroponics/SENSOR",
            payload='{"Time":"2023-05-19T20:52:56","BME280":{"Temperature":17.0,"Humidity":53.4,"DewPoint":7.4,"Pressure":984.0},"PressureUnit":"hPa","TempUnit":"C"}',
        ),
    )

    write_sql_mock.assert_called_with(
        "tasmota_bme280",
        {
            "time": "2023-05-19T20:52:56",
            "topic": "tele/node_mcu_hydroponics/SENSOR",
            "dew_point": 7.4,
            "humidity": 53.4,
            "pressure": 984.0,
            "temperature": 17.0,
        },
    )


def test_pms7003_sensor(sensor_sut, write_sql_mock, mocker):
    sensor_sut._on_tele_sensor(
        "",
        {},
        mocker.Mock(
            topic="tele/living-room/SENSOR",
            payload='{"Time": "2024-04-07T20:24:31.135531", "PMS7003": {"pm1_0cf1": 4, "pm2_5cf1": 6, "pm10cf1": 9, "pm1_0": 4, "pm2_5": 6, "pm10": 9, "n0_3": 1155, "n0_5": 312, "n1_0": 46, "n2_5": 6, "n5_0": 4, "n10": 0}}',
        ),
    )

    write_sql_mock.assert_called_with(
        "tasmota_pms7003",
        {
            "time": "2024-04-07T20:24:31.135531",
            "topic": "tele/living-room/SENSOR",
            "pm1_0cf1": 4,
            "pm2_5cf1": 6,
            "pm10cf1": 9,
            "pm1_0": 4,
            "pm2_5": 6,
            "pm10": 9,
            "n0_3": 1155,
            "n0_5": 312,
            "n1_0": 46,
            "n2_5": 6,
            "n5_0": 4,
            "n10": 0,
        },
    )


def test_hichi_sensor(sensor_sut, write_sql_mock, mocker):
    sensor_sut._on_tele_sensor(
        "",
        {},
        mocker.Mock(
            topic="tele/hichi/SENSOR",
            payload='{"Time":"2023-05-19T20:46:49","":{"total":10163360.8,"tariff_1":10163360.8,"tariff_2":0.0,"neg_total":131712.5,"neg_tariff_1":131712.5,"neg_tariff_2":0.0,"current":253.4}}',
        ),
    )

    write_sql_mock.assert_called_with(
        "tasmota_hichi",
        {
            "time": "2023-05-19T20:46:49",
            "topic": "tele/hichi/SENSOR",
            "total": 10163360.8,
            "tariff_1": 10163360.8,
            "tariff_2": 0.0,
            "neg_total": 131712.5,
            "neg_tariff_1": 131712.5,
            "neg_tariff_2": 0.0,
            "current": 253.4,
        },
    )


def test_sds0x1_sensor(sensor_sut, write_sql_mock, mocker):
    sensor_sut._on_tele_sensor(
        "",
        {},
        mocker.Mock(
            topic="tele/node_mcu_terrace/SENSOR",
            payload='{"Time":"2023-05-21T01:06:38","BME280":{"Temperature":20.5,"Humidity":53.1,"DewPoint":10.6,"Pressure":977.0},"SDS0X1":{"PM2.5":11.8,"PM10":5.8},"PressureUnit":"hPa","TempUnit":"C"}',
        ),
    )

    write_sql_mock.assert_any_call(
        "tasmota_bme280",
        {
            "time": "2023-05-21T01:06:38",
            "topic": "tele/node_mcu_terrace/SENSOR",
            "dew_point": 10.6,
            "humidity": 53.1,
            "pressure": 977.0,
            "temperature": 20.5,
        },
    )
    write_sql_mock.assert_called_with(
        "tasmota_sds0x1",
        {
            "time": "2023-05-21T01:06:38",
            "topic": "tele/node_mcu_terrace/SENSOR",
            "pm2_5": 11.8,
            "pm10": 5.8,
        },
    )


def test_watermeter(sensor_sut, write_sql_mock, mocker):
    sensor_sut._on_watermeter(
        "",
        {},
        mocker.Mock(
            topic="watermeter/main/json",
            payload='{ "value": "545.2518", "raw": "00545.2518", "pre": "545.2518", "error": "no error", "rate": "0.000000", "timestamp": "2024-05-01T19:05:19+0200" }',
        ),
    )

    write_sql_mock.assert_called_with(
        "watermeter",
        {"time": "2024-05-01T17:05:19+00:00", "topic": "watermeter/main/json", "value": 545.2518},
    )


def test_ignore_LWT(sensor_sut, write_sql_mock, mocker):
    sensor_sut._on_tele_sensor("", {}, mocker.Mock(topic="tele/node_mcu_hydroponics/LWT", payload="Online"))

    write_sql_mock.assert_not_called()


def test_analog_sensor(sensor_sut, write_sql_mock, mocker):
    sensor_sut._on_tele_sensor(
        "",
        {},
        mocker.Mock(
            topic="tele/d1_mini_soil_moisture_1/SENSOR",
            payload='{"Time":"2024-01-13T20:25:03","ANALOG":{"A0":591}}',
        ),
    )

    write_sql_mock.assert_any_call(
        "tasmota_analog",
        {
            "time": "2024-01-13T20:25:03",
            "topic": "tele/d1_mini_soil_moisture_1/SENSOR",
            "analog": 591,
        },
    )


# def test_psql_integration():
# sql_conn = psycopg.connect(conninfo="postgresql://postgres@localhost/mqtt")
# sql_conn.commit()

# data = {"time": "2023-05-21T01:06:38", "topic": "tele/node_mcu_terrace/SENSOR", "dew_point": 10.6, "humidity": 53.1, "pressure": 977.0, "temperature": 20.5}
# statement = psycopg.sql.SQL("INSERT INTO {}({}) VALUES({})").format(psycopg.sql.Identifier("tasmota_bme280"), psycopg.sql.SQL(", ").join(map(psycopg.sql.Identifier, data.keys())), psycopg.sql.SQL(", ").join(map(psycopg.sql.Placeholder, data.keys())))
# sql_conn.execute(statement, data)
# sql_conn.commit()

# data = {"time": "2023-05-21T01:06:38", "topic": "tele/node_mcu_terrace/SENSOR", "pm2_5": 11.8, "pm10": 5.8}
# statement = psycopg.sql.SQL("INSERT INTO {}({}) VALUES({})").format(psycopg.sql.Identifier("tasmota_sds0x1"), psycopg.sql.SQL(", ").join(map(psycopg.sql.Identifier, data.keys())), psycopg.sql.SQL(", ").join(map(psycopg.sql.Placeholder, data.keys())))
# sql_conn.execute(statement, data)
# sql_conn.commit()

# print("foo")
# publish.single("topic", "test", hostname="localhost", port=1883)
# print("bar")

# MqttToTimescaledb("postgresql://postgres@localhost/mqtt", "localhost", 1883, "test")


# publish.single("test", "payload2", hostname="127.0.0.1")
