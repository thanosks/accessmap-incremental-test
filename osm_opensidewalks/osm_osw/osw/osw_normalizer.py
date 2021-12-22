class OSWWayNormalizer:
    ROAD_HIGHWAY_VALUES = (
        "primary",
        "secondary",
        "tertiary",
        "residential",
        "service",
    )

    def __init__(self, tags):
        self.tags = tags

    def filter(self):
        return (
            self.is_sidewalk()
            or self.is_crossing()
            or self.is_footway()
            or self.is_road()
        )

    @staticmethod
    def osw_way_filter(tags):
        return OSWWayNormalizer(tags).filter()

    def normalize(self):
        if self.is_sidewalk():
            return self._normalize_sidewalk()
        elif self.is_crossing():
            return self._normalize_crossing()
        elif self.is_footway():
            return self._normalize_footway()
        elif self.is_road():
            return self._normalize_road()
        else:
            raise ValueError("This is an invalid way")

    def _normalize_footway(self):
        new_tags = {
            "highway": "footway",
        }
        if "width" in self.tags:
            try:
                new_tags["width"] = float(self.tags["width"])
            except ValueError:
                pass
        if "incline" in self.tags:
            try:
                new_tags["incline"] = float(self.tags["incline"])
            except ValueError:
                pass

        return new_tags

    def _normalize_sidewalk(self):
        new_tags = self._normalize_footway()
        new_tags["footway"] = "sidewalk"

        return new_tags

    def _normalize_crossing(self):
        new_tags = self._normalize_footway()
        new_tags["footway"] = "crossing"
        if "crossing" in self.tags:
            if self.tags["crossing"] in (
                "marked",
                "uncontrolled",
                "traffic_signals",
                "zebra",
            ):
                new_tags["crossing"] = "marked"
            elif self.tags["crossing"] in "unmarked":
                new_tags["crossing"] = "unmarked"

        return new_tags

    def _normalize_road(self):
        new_tags = {"highway": self.tags["highway"]}
        if "width" in self.tags:
            try:
                new_tags["width"] = float(self.tags["width"])
            except ValueError:
                pass

        return new_tags

    def is_sidewalk(self):
        return (self.tags.get("highway", "") == "footway") and (
            self.tags.get("footway", "") == "sidewalk"
        )

    def is_crossing(self):
        return (self.tags.get("highway", "") == "footway") and (
            self.tags.get("footway", "") == "crossing"
        )

    def is_footway(self):
        return self.tags.get("highway", "") == "footway"

    def is_road(self):
        return self.tags.get("highway", "") in self.ROAD_HIGHWAY_VALUES


class OSWNodeNormalizer:
    KERB_VALUES = ("flush", "lowered", "rolled", "raised")

    def __init__(self, tags):
        self.tags = tags

    def filter(self):
        return self.is_kerb()

    @staticmethod
    def osw_node_filter(tags):
        return OSWNodeNormalizer(tags).filter()

    def normalize(self):
        if self.is_kerb():
            return self._normalize_kerb()
        else:
            raise ValueError("This is an invalid node")

    def _normalize_kerb(self):
        if "barrier" in self.tags:
            del self.tags["barrier"]

        keep_keys = ["kerb", "tactile_surface"]
        new_tags = {}
        for tag in keep_keys:
            if tag in self.tags:
                new_tags[tag] = self.tags[tag]

        return new_tags

    def is_kerb(self):
        return self.tags.get("kerb", "") in self.KERB_VALUES
