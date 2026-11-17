CATALOG_READY_KEY = "catalog:ready"
ACTIVE_SESSION_CONFIG_KEY = "session:active_config"


def catalog_class_key(class_id: str) -> str:
    return f"catalog:class:{class_id}"


def slot_counter_key(class_id: str) -> str:
    return f"slot:counter:{class_id}"


def student_state_key(student_id: str) -> str:
    return f"student:state:{student_id}"
