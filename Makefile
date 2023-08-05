NAME := tasmota_mqtt_to_psql
INSTALL_STAMP := .install.stamp
POETRY := $(shell command -v poetry 2> /dev/null)

.DEFAULT_GOAL := run

install: $(INSTALL_STAMP)
$(INSTALL_STAMP): pyproject.toml poetry.lock
	@if [ -z $(POETRY) ]; then echo "Poetry could not be found. See https://python-poetry.org/docs/"; exit 2; fi
	$(POETRY) install
	touch $(INSTALL_STAMP)

.PHONY: clean
clean:
	find . -type d -name "__pycache__" | xargs rm -rf {};
	rm -rf $(INSTALL_STAMP) .coverage .mypy_cache .pytest_cache

.PHONY: lint
lint: $(INSTALL_STAMP)
	$(POETRY) run isort --profile=black --lines-after-imports=2 --check-only ./tests/ $(NAME)
	$(POETRY) run black --check ./tests/ $(NAME) --diff
	$(POETRY) run flake8 --ignore=W503,E501 ./tests/ $(NAME)
	$(POETRY) run mypy ./tests/ $(NAME) --ignore-missing-imports
	$(POETRY) run bandit -r $(NAME) -s B608

.PHONY: format
format: $(INSTALL_STAMP)
	$(POETRY) run isort --profile=black --lines-after-imports=2 ./tests/ $(NAME)
	$(POETRY) run black ./tests/ $(NAME)

.PHONY: test
test: $(INSTALL_STAMP)
	$(POETRY) run pytest ./tests/ --cov-report term-missing --cov-fail-under 60 --cov $(NAME)

.PHONY: testc
testc: $(INSTALL_STAMP)
	while inotifywait -q -e modify tests $(NAME) -r; do $(POETRY) run pytest -s ./tests/ --cov-report term-missing --cov-fail-under 60 --cov $(NAME); done

.PHONY: run
run: $(INSTALL_STAMP)
	# podman run --rm -p 127.0.0.1:5432:5432 --name postgres -e POSTGRES_HOST_AUTH_METHOD=trust -d docker.io/postgres
	# while ! podman exec -it postgres pg_isready -U postgres ; do sleep 0.1; done
	# sleep 1 # postgres is restarting after initialization
	# while ! podman exec -it postgres pg_isready -U postgres ; do sleep 0.1; done
	# podman exec -it postgres psql -U postgres \
	# 	-c "DROP DATABASE IF EXISTS mqtt;" \
	# 	-c "CREATE DATABASE mqtt;" \
	# 	-c "\c mqtt" \
	# 	-c "CREATE TABLE IF NOT EXISTS tasmota_bme280 (time TIMESTAMPTZ NOT NULL, topic VARCHAR(50) NOT NULL, dew_point NUMERIC NOT NULL, humidity NUMERIC NOT NULL, pressure NUMERIC NOT NULL, temperature NUMERIC NOT NULL);" \
	# 	-c "CREATE TABLE IF NOT EXISTS tasmota_energy ( time TIMESTAMPTZ NOT NULL, topic VARCHAR(50) NOT NULL, total NUMERIC NOT NULL, power NUMERIC NOT NULL, apparent_power NUMERIC NOT NULL, reactive_power NUMERIC NOT NULL, factor NUMERIC NOT NULL, voltage NUMERIC NOT NULL, current NUMERIC NOT NULL);" \
	# 	-c "CREATE TABLE IF NOT EXISTS tasmota_hichi (time TIMESTAMPTZ NOT NULL, topic VARCHAR(50) NOT NULL, total NUMERIC NOT NULL, tariff_1 NUMERIC NOT NULL, tariff_2 NUMERIC NOT NULL, neg_total NUMERIC NOT NULL, neg_tariff_1 NUMERIC NOT NULL, neg_tariff_2 NUMERIC NOT NULL, current NUMERIC NOT NULL);" \
	# 	-c "CREATE TABLE IF NOT EXISTS tasmota_sds0x1 (time TIMESTAMPTZ NOT NULL, topic VARCHAR(50) NOT NULL, pm2_5 NUMERIC NOT NULL, pm10 NUMERIC NOT NULL);" \
	# 	-c "CREATE TABLE IF NOT EXISTS tasmota_state (time TIMESTAMPTZ NOT NULL, topic VARCHAR(50) NOT NULL, load_avg NUMERIC NOT NULL, wifi_rssi NUMERIC NOT NULL, wifi_signal NUMERIC NOT NULL, wifi_link_count NUMERIC NOT NULL);"

	# podman run --rm -p 127.0.0.1:1883:1883 --name mqtt -d docker.io/eclipse-mosquitto sh -c 'echo -e "listener 1883\nallow_anonymous true" > /mosquitto/config/mosquitto.conf && mosquitto -c /mosquitto/config/mosquitto.conf'

	$(POETRY) run python ./$(NAME)/$(NAME).py --db_connection_string="postgresql://postgres@localhost/mqtt" --mqtt_host=localhost --mqtt_client_id=test --log=DEBUG

	# podman exec -it mqtt mosquitto_pub -h localhost -t "tele/node_mcu_terrace/SENSOR" -m '{"Time":"2023-05-21T01:06:38","BME280":{"Temperature":20.5,"Humidity":53.1,"DewPoint":10.6,"Pressure":977.0},"SDS0X1":{"PM2.5":11.8,"PM10":5.8},"PressureUnit":"hPa","TempUnit":"C"}'
	# podman exec -it postgres psql -U postgres -d mqtt 

.PHONY: container
container:
	podman build -t mr_moe/tasmota_mqtt_to_psql .
	podman save mr_moe/tasmota_mqtt_to_psql | zstd -19 --long -T0 > ../tasmota_mqtt_to_psql.tar.zst

.PHONY: container-run
container-run:
	podman run --rm -it mr_moe/tasmota_mqtt_to_psql
	# https://stackoverflow.com/a/62060460
