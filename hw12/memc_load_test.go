package main

import (
	"./appsinstalled"
	"bufio"
	"github.com/golang/protobuf/proto"
	"reflect"
	"strings"
	"testing"
)

func TestParseLine(t *testing.T) {
	sample := "idfa\tt1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\ngaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"

	scanner := bufio.NewScanner(strings.NewReader(sample))
	for scanner.Scan() {
		appsInstalled, err := parseAppsInstalled(scanner.Text())
		if err != nil {
			t.Error("Parse line error:", err)
			continue
		}
		ua := &appsinstalled.UserApps{
			Lat:  proto.Float64(appsInstalled.lat),
			Lon:  proto.Float64(appsInstalled.lon),
			Apps: appsInstalled.apps,
		}
		packed, err := proto.Marshal(ua)
		if err != nil {
			t.Error("Marshaling error:", err)
		}
		unpacked := &appsinstalled.UserApps{}
		err = proto.Unmarshal(packed, unpacked)
		if err != nil {
			t.Error("Unmarshaling error:", err)
		}

		if ua.GetLat() != unpacked.GetLat() {
			t.Errorf("'Lat' Data mismatch %g != %g", ua.GetLat(), unpacked.GetLat())
		}
		if ua.GetLon() != unpacked.GetLon() {
			t.Errorf("'Lon' Data mismatch %g != %g", ua.GetLon(), unpacked.GetLon())
		}

		if !reflect.DeepEqual(ua.GetApps(), unpacked.GetApps()) {
			t.Errorf("'Apps' Data mismatch %v != %v", ua.GetApps(), unpacked.GetApps())
		}
	}
	if err := scanner.Err(); err != nil {
		t.Error("Unexpected error:", err)
	}
}
