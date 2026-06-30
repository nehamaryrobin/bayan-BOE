from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class BoeHeader:
    DEC_NO: str
    PDF_FILENAME: str
    DEC_DATE_HIJRI_2: Optional[str] = None
    DEC_DATE_GREGORIAN_2: Optional[str] = None
    DEC_TYPE_3: Optional[str] = None
    PORT_TYPE_4: Optional[str] = None
    DELIVERY_ORDER_NO_5: Optional[str] = None
    IMPORTER_EXPORTER_6: Optional[str] = None
    UNLOAD_DATE_7A: Optional[str] = None
    NET_WEIGHT_7B: Optional[str] = None
    CARRIER_CAPTAIN_DRIVER_8: Optional[str] = None
    INTERCESSOR_CO_9: Optional[str] = None
    GROSS_WEIGHT_10: Optional[str] = None
    CARRIER_NAME_11: Optional[str] = None
    COMMERCIAL_REG_NO_12: Optional[str] = None
    TIN_NO_12A: Optional[str] = None
    MEASUREMENT_13: Optional[str] = None
    VOYAGE_FLIGHT_NO_14: Optional[str] = None
    EXPORTED_TO_15: Optional[str] = None
    PACKAGES_16: Optional[str] = None
    AWB_NO_17A: Optional[str] = None
    MANIFEST_NO_17B: Optional[str] = None
    PORT_OF_LOADING_18: Optional[str] = None
    MARKS_NUMBERS_19: Optional[str] = None
    PORT_OF_DISCHARGE_20: Optional[str] = None
    DESTINATION_21: Optional[str] = None
    CLEARING_AGENT_38: Optional[str] = None
    LICENCE_NO_39: Optional[str] = None
    UNIFIED_CUSTOMS_CODE_43: Optional[str] = None
    GCC_AEO_CODE_44: Optional[str] = None
    OTHER_REMARKS_45: Optional[str] = None
    EXIT_PORT_46: Optional[str] = None
    TOTAL_DUTY_48: Optional[str] = None
    VAT_48A: Optional[str] = None
    EXCISE_TAX_48B: Optional[str] = None
    ANTI_DUMPING_48C: Optional[str] = None
    HANDLING_49: Optional[str] = None
    OTHER_CHARGES_50: Optional[str] = None
    DEFINITE_51: Optional[str] = None
    INSURED_52: Optional[str] = None
    PAYMENT_METHOD_53: Optional[str] = None
    PAYMENT_NO_54: Optional[str] = None
    PAYMENT_DATE_55: Optional[str] = None
    PAYMENT_BANK_56: Optional[str] = None
    RECEIPT_NO_57: Optional[str] = None
    RECEIPT_DATE_58: Optional[str] = None
    RECEIPT_BANK_59: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BoeLineItem:
    DEC_NO: str
    PDF_FILENAME: str
    ITEM_NO: int
    HS_CODE_22: Optional[str] = None
    GOODS_DESCRIPTION_23: Optional[str] = None
    ORIGIN_24: Optional[str] = None
    FOREIGN_VALUE_25: Optional[str] = None
    CURRENCY_TYPE_26: Optional[str] = None
    CURRENCY_VALUE_27: Optional[str] = None
    CIF_LOCAL_VALUE_28: Optional[str] = None
    D_RATE_29: Optional[str] = None
    INCOME_TYPE_30: Optional[str] = None
    TOTAL_DUTY_31: Optional[str] = None
    PKG_QTY_32: Optional[str] = None
    PKG_TYPE_33: Optional[str] = None
    ITEM_QTY_34: Optional[str] = None
    ITEM_UNIT_35: Optional[str] = None
    NET_WEIGHT_36: Optional[str] = None
    GROSS_WEIGHT_37: Optional[str] = None
    AIP_NO_37A: Optional[str] = None
    AIP_DUTY_37B: Optional[str] = None
    CUSTOMS_RESTRICTIONS_AGENCY_40: Optional[str] = None
    CUSTOMS_RELEASE_REF_41: Optional[str] = None
    EXEMPTION_CODE_42: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)
