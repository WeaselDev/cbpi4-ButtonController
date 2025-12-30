# Craftbeerpi4 Plugin for using pushbuttons as sensors
This plugin allows you to configure some GPIOs as sensors to perform various actions in Craftbeerpi V4. 

## Software installation:
This version requires Craftbeerpi V4 version 4.6.0 and above.

Please have a look at the [Craftbeerpi4 Documentation](https://openbrewing.gitbook.io/craftbeerpi4_support/readme/plugin-installation)

- Package name: cbpi4-ButtonController
- Package link: https://github.com/WeaselDev/cbpi4-ButtonController/archive/main.zip

## Hardware Installation:

Connect your pushbuttons to any unsused GPIO
The GPIO will be configured as Input with internal pullup resistor.

## Sensor Configuration

The sensor must be configured on the hardware page. 
Configure one instance per button.
The following parameters can be set:
- GPIO_BUTTON: BCM Number of the used GPIO
- DEBOUNCE_TIME: Time in ms to debounce the input (100-200ms seems to be a good value)
- BUTTON_ACTION: Four actions are defined:
	- toggle_actor: Will toggle one output like the relais for heating or an agitator
	- add_time: Add a configurable time in minutes to the timer of the active step. (Not working right now)
	- next_step: Activate the next step (Not working right now)
	- all_off: Will disable all outputs like heating, agitator, pump,...
- Actor: Select the actor to toggle. (Only used for toggle_actor buttons)
- TIME_TO_ADD: Minutes to add to the active step. (Only used for add_time buttons)

### Changelog:

- (0.1.0) First version with some flaws