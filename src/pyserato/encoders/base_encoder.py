from abc import abstractmethod, ABC

from pyserato.model.track import Track


class BaseEncoder(ABC):

    @property
    @abstractmethod
    def tag_name(self) -> str:
        pass

    @property
    @abstractmethod
    def tag_version(self) -> bytes:
        pass

    @property
    @abstractmethod
    def markers_name(self) -> str:
        pass

    @abstractmethod
    def write(self, track: Track):
        pass
