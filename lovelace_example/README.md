### Lovelace card example with sorted price information
In this example we make a simple but useful lovelace card with price information sorted in ascending order. Especially during periods where the price difference is large, it's useful to sort out the cheapest hours throughout the day and day ahead. In addition, to make this work, you need to install the HACS plugins "Flex Table" and "Multiple Entity Row".

The final result will look like this:

![Simple](/lovelace_example/semopx.png)

First of all we have to make a sensor for each hour. This can be done using the provided python script or by manually making template sensors in sensors.yaml. In this example we make template sensors. If you live in another price area than "Krsand" your semopx sensors entity id will be different from mine. So remember to replace "sensor.semopx_kwh_krsand_nok_2_095_025" with your own. Your "unit_of_measurement" may also be different from mine as well.
Add to your sensors.yaml:
````
# TEMPLATE SENSORS
- platform: template
  sensors:
    # SEMOPX PRICES
    semopx_today_hr_00_01:
      entity_id: sensor.semopx_kwh_krsand_nok_2_095_025
      friendly_name: "Today hour 1"
      icon_template: mdi:cash
      unit_of_measurement: "øre"
      value_template: "{{ states.sensor.semopx_kwh_krsand_nok_2_095_025.attributes.today[0] }}"

    semopx_today_hr_01_02:
      entity_id: sensor.semopx_kwh_krsand_nok_2_095_025
      friendly_name: "Today hour 2"
      icon_template: mdi:cash
      unit_of_measurement: "øre"
      value_template: "{{ states.sensor.semopx_kwh_krsand_nok_2_095_025.attributes.today[1] }}"

### and so on down to...

    semopx_today_hr_23_24:
      entity_id: sensor.semopx_kwh_krsand_nok_2_095_025
      friendly_name: "Today hour 24"
      icon_template: mdi:cash
      unit_of_measurement: "øre"
      value_template: "{{ states.sensor.semopx_kwh_krsand_nok_2_095_025.attributes.today[23] }}"

### and than for the day ahead...

    semopx_tomorrow_hr_00_01:
      entity_id: sensor.semopx_kwh_krsand_nok_2_095_025
      friendly_name: "Tomorrow hour 1"
      icon_template: mdi:cash
      unit_of_measurement: "øre"
      value_template: "{{ states.sensor.semopx_kwh_krsand_nok_2_095_025.attributes.tomorrow[0] }}"

    semopx_tomorrow_hr_01_02:
      entity_id: sensor.semopx_kwh_krsand_nok_2_095_025
      friendly_name: "Tomorrow hour 2"
      icon_template: mdi:cash
      unit_of_measurement: "øre"
      value_template: "{{ states.sensor.semopx_kwh_krsand_nok_2_095_025.attributes.tomorrow[1] }}"

### and so on down to...

    semopx_tomorrow_hr_23_24:
      entity_id: sensor.semopx_kwh_krsand_nok_2_095_025
      friendly_name: "Tomorrow hour 24"
      icon_template: mdi:cash
      unit_of_measurement: "øre"
      value_template: "{{ states.sensor.semopx_kwh_krsand_nok_2_095_025.attributes.tomorrow[23] }}"
      
````

Save and restart Home Assistant to see that the new sensors works properly.

Now we can make the lovelace card. In this example we use ui-lovelace.yaml (mode: yaml # in configuration.yaml) and the card has it's own view called "Energy prices".
Add the following to your ui-lovelace.yaml:

````
title: My Home Assistant
views:
  - title: Energy prices
    icon: mdi:cash
    background: white
    cards:
      - type: vertical-stack
        cards:
          - type: entities
            title: Energy prices
            show_header_toggle: false
            entities:
              - entity: sensor.semopx_kwh_krsand_nok_2_095_025
                type: custom:multiple-entity-row
                name: Todays prices (øre/kWh)
                unit: " "
                icon: mdi:cash-multiple
                show_state: False
                entities:
                  - attribute: min
                    name: Min
                  - attribute: max
                    name: Max
                  - attribute: current_price
                    name: Current
                secondary_info:
                  entity: sensor.semopx_kwh_krsand_nok_2_095_025
                  attribute: average
                  name: "Average:"
          - type: custom:flex-table-card
            sort_by: state+
            entities:
              include: sensor.semopx_today_h*
            columns:
              - name: Today (sorted ascending)
                prop: name
              - name: Price (øre/kWh)
                prop: state
                align: right
          - type: custom:flex-table-card
            sort_by: state+
            entities:
              include: sensor.semopx_tomorrow_h*
            columns:
              - name: Tomorrow (sorted ascen.)
                prop: name
              - name: Price (øre/kWh)
                prop: state
                align: right
````
    
Reload the lovelace views and enjoy your new card.
