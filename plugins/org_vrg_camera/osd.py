from dataclasses import asdict, dataclass

from sdk.videoreg import Videoreg

WEIGHT_TITLE = 0
WEIGHT_TIME = 10
WEIGHT_GPS = 20
WEIGHT_LBS = 30
WEIGHT_CHRG = 40
WEIGHT_BAT = 50
WEIGHT_CPU = 60


@dataclass
class Token:
  key: str
  text: str
  weight: int

  def to_dict(self):
    return asdict(self)


title_token = Token(key="title", text="VIDEOREG.ORG", weight=WEIGHT_TITLE)
time_token = Token(key="time", text="%F %T", weight=WEIGHT_TIME)


class OSD:
  _videoreg: Videoreg
  _state: list[Token]

  def __init__(self, videoreg: Videoreg):
    self._videoreg = videoreg
    self._state = [title_token, time_token]

  def update(self, patch: list[Token]):
    for updated_token in patch:
      existed_token = next((t for t in self._state if t.key == updated_token.key), None)

      if existed_token:
        existed_token.text = updated_token.text
        existed_token.weight = updated_token.weight
      else:
        self._state.append(updated_token)

    sorted_tokens = sorted(self._state, key=lambda t: t.weight)
    texts = [t.text for t in sorted_tokens if t.text]

    rpicam_annotate_file = self._videoreg.private_path("camera-annotate.txt")
    with open(rpicam_annotate_file, "w") as f:
      f.write(" ".join(texts))

  def reset(self):
    self._state = [title_token, time_token]
    rpicam_annotate_file = self._videoreg.private_path("camera-annotate.txt")
    with open(rpicam_annotate_file, "w") as f:
      f.write(f"{title_token.text} {time_token.text}")
