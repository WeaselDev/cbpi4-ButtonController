# -*- coding: utf-8 -*-
import logging
import asyncio
from cbpi.api import *
from gpiozero import Button, Device
from gpiozero.exc import GPIOPinInUse

logger = logging.getLogger(__name__)

@parameters([
    Property.Number(label="GPIO_BUTTON", configurable=True, default_value=17, description="GPIO Pin für den Taster"),
    Property.Number(label="DEBOUNCE_TIME", configurable=True, default_value=20, description="Debounce Zeit in Millisekunden"),
    Property.Select(label="BUTTON_ACTION", options=["toggle_actor", "add_time", "next_step", "all_off"], 
                    description="Aktion des Tasters"),
    Property.Actor(label="ACTUATOR_ID", description="Aktuator (nur für Toggle-Aktion)"),
    Property.Number(label="TIME_TO_ADD", configurable=True, default_value=5, description="Minuten hinzufügen")
])
class GPIOSensor(CBPiSensor):
    """GPIO Button Plugin für CraftBeerPi4"""
    
    _active_buttons = {}  # Klassen-Variable für Pin-Verwaltung

    def __init__(self, cbpi, id, props):
        super().__init__(cbpi, id, props)
        self.button = None
        self.gpio_pin = None
        self.loop = None
        self.button_action = None
        self.actor = None
        self.time_to_add = 5

    async def on_start(self):
        """Startet das Plugin und konfiguriert den GPIO-Taster"""
        self.loop = asyncio.get_event_loop()
        
        # Konfiguration laden
        self.gpio_pin = int(self.props.get("GPIO_BUTTON", 17))
        self.button_action = self.props.get("BUTTON_ACTION", "toggle_actor")
        self.actor = self.props.get("ACTUATOR_ID")
        self.time_to_add = int(self.props.get("TIME_TO_ADD", 5))
        debounce_time = float(self.props.get("DEBOUNCE_TIME", 20)) / 1000.0

        logger.info(f"GPIO{self.gpio_pin} - Aktion: {self.button_action}")

        # Pin VOLLSTÄNDIG freigeben bevor wir starten
        await self._force_cleanup_pin()

        # Button erstellen mit Retry
        for attempt in range(3):
            try:
                self.button = Button(self.gpio_pin, bounce_time=debounce_time, pull_up=True)
                self.button.when_pressed = self._button_pressed_sync
                GPIOSensor._active_buttons[self.gpio_pin] = self.button
                logger.info(f"✓ GPIO{self.gpio_pin} konfiguriert")
                break
            except GPIOPinInUse as e:
                if attempt < 2:
                    logger.warning(f"GPIO{self.gpio_pin} noch belegt (Versuch {attempt + 1}/3), räume auf...")
                    await self._force_cleanup_pin()
                    await asyncio.sleep(0.5)
                else:
                    logger.error(f"GPIO{self.gpio_pin} konnte nach 3 Versuchen nicht initialisiert werden")
                    raise

    async def on_stop(self):
        """Beendet das Plugin"""
        logger.info(f"Stoppe GPIO{self.gpio_pin}")
        await self._cleanup_button()

    async def _force_cleanup_pin(self):
        """AGGRESSIVE Pin-Bereinigung - räumt ALLES auf"""
        try:
            # 1. Alten Button aus unserem Dictionary schließen
            if self.gpio_pin in GPIOSensor._active_buttons:
                old_button = GPIOSensor._active_buttons[self.gpio_pin]
                try:
                    old_button.when_pressed = None
                    old_button.close()
                    logger.debug(f"Dictionary-Button auf GPIO{self.gpio_pin} geschlossen")
                except Exception as e:
                    logger.debug(f"Dictionary-Button-Close-Fehler (ignoriert): {e}")
                del GPIOSensor._active_buttons[self.gpio_pin]
                await asyncio.sleep(0.2)

            # 2. Pin auf Factory-Ebene freigeben (DER WICHTIGE TEIL!)
            if Device.pin_factory:
                try:
                    # Hole die Pin-Instanz direkt von der Factory
                    pin = Device.pin_factory.pin(self.gpio_pin)
                    if pin:
                        # Lösche die Reservierung in der Factory
                        if hasattr(Device.pin_factory, '_reservations'):
                            if pin in Device.pin_factory._reservations:
                                del Device.pin_factory._reservations[pin]
                                logger.debug(f"Pin-Reservierung für GPIO{self.gpio_pin} gelöscht")
                        
                        # Schließe den Pin
                        pin.close()
                        logger.debug(f"Pin-Objekt für GPIO{self.gpio_pin} geschlossen")
                except Exception as e:
                    logger.debug(f"Factory-Cleanup-Fehler (ignoriert): {e}")

            await asyncio.sleep(0.3)
            logger.debug(f"✓ GPIO{self.gpio_pin} vollständig freigegeben")

        except Exception as e:
            logger.debug(f"Force-Cleanup allgemeiner Fehler (ignoriert): {e}")

    async def _cleanup_button(self):
        """Räumt Button-Ressourcen auf"""
        if self.button:
            try:
                self.button.when_pressed = None
                self.button.close()
                logger.debug(f"Button GPIO{self.gpio_pin} geschlossen")
            except Exception as e:
                logger.error(f"Cleanup-Fehler: {e}")
            self.button = None
        
        if self.gpio_pin in GPIOSensor._active_buttons:
            del GPIOSensor._active_buttons[self.gpio_pin]

    def _button_pressed_sync(self):
        """Synchroner Wrapper für async Callback"""
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._button_pressed(), self.loop)

    async def _button_pressed(self):
        """Führt die konfigurierte Aktion aus"""
        logger.info(f"🔘 GPIO{self.gpio_pin} gedrückt - {self.button_action}")
        
        actions = {
            "toggle_actor": self._toggle_actor,
            "add_time": self._add_time,
            "next_step": self._next_step,
            "all_off": self._all_off
        }
        
        action = actions.get(self.button_action)
        if action:
            try:
                await action()
            except Exception as e:
                logger.error(f"Fehler bei {self.button_action}: {e}")

    async def _toggle_actor(self):
        """Schaltet Aktuator ein/aus"""
        if not self.actor:
            return logger.warning("Kein Aktuator konfiguriert")

        actor = self.cbpi.actor.find_by_id(self.actor)
        if not actor:
            return logger.error(f"Aktuator {self.actor} nicht gefunden")

        if actor.instance.state:
            await self.cbpi.actor.off(self.actor)
            logger.info(f"✓ Aktuator {self.actor} AUS")
        else:
            await self.cbpi.actor.on(self.actor, 100)
            logger.info(f"✓ Aktuator {self.actor} EIN")

    async def _add_time(self):
        """Addiert Zeit zum aktuellen Step"""
        if not hasattr(self.cbpi, 'step'):
            return logger.error("Step-API nicht verfügbar")

        current_step_id = self.cbpi.step.current_step
        if not current_step_id:
            return logger.warning("Kein aktiver Step")

        current_step = self.cbpi.step.find_by_id(current_step_id)
        if not current_step or not hasattr(current_step.instance, 'timer'):
            return logger.warning("Step hat keinen Timer")

        if current_step.instance.timer:
            current_step.instance.timer.end += self.time_to_add * 60
            logger.info(f"✓ {self.time_to_add} Minuten hinzugefügt")

    async def _next_step(self):
        """Startet den nächsten Step"""
        if not hasattr(self.cbpi, 'step'):
            return logger.error("Step-API nicht verfügbar")

        if not self.cbpi.step.current_step:
            return logger.warning("Kein aktiver Step")

        await self.cbpi.step.next()
        logger.info("✓ Nächster Step gestartet")

    async def _all_off(self):
        """Schaltet alle Aktuatoren aus"""
        if not hasattr(self.cbpi, 'actor'):
            return logger.error("Aktuator-API nicht verfügbar")

        actors = self.cbpi.actor.get_all()
        count = 0
        
        for actor in actors:
            try:
                await self.cbpi.actor.off(actor.id)
                count += 1
            except Exception as e:
                logger.error(f"Fehler bei Aktuator {actor.id}: {e}")

        logger.info(f"✓ {count} Aktuatoren ausgeschaltet")

    async def run(self):
        """Hauptloop"""
        while self.running:
            await asyncio.sleep(1)

def setup(cbpi):
    """Plugin-Registrierung"""
    cbpi.plugin.register("GPIOSensor", GPIOSensor)
