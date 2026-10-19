from aiogram.fsm.state import State, StatesGroup


class VinInspectorStates(StatesGroup):
    waiting_for_vin = State()
    waiting_for_oem = State()
