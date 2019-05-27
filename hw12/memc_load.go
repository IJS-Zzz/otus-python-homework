package main

import (
	"./appsinstalled"
	"bufio"
	"compress/gzip"
	"errors"
	"flag"
	"fmt"
	"github.com/bradfitz/gomemcache/memcache"
	"github.com/golang/protobuf/proto"
	"log"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"time"
)

const (
	MemcacheTimeout = 500 * time.Millisecond
	NormalErrRate   = 0.01
)

type AppsInstalled struct {
	devType string
	devId   string
	lat     float64
	lon     float64
	apps    []uint32
}

type Options struct {
	dryRun  bool
	log     bool
	logPath string
	pattern string
	workers int
	buffer  int
	idfa    string
	gaid    string
	adid    string
	dvid    string
}

type Statistic struct {
	file      string
	processed int
	errors    int
}

type Memcache struct {
	address    string
	connection *memcache.Client
}

type MemcacheItem struct {
	key   string
	value []byte
}

// ##############################
// SERVICE
// ##############################

func parseArgs() (options Options) {
	// run options
	flag.BoolVar(&options.dryRun, "dry", false, "debug mode (without sending to memcached)")

	// logging
	flag.BoolVar(&options.log, "log", false, "enable write logging")
	flag.StringVar(&options.logPath, "logpath", "./memc.log", "path to log file")
	flag.StringVar(&options.pattern, "pattern", "/data/appsinstalled/*.tsv.gz", "files path pattern")

	// workers settings
	flag.IntVar(&options.workers, "workers", runtime.NumCPU(), "number of file in parallel processing")
	flag.IntVar(&options.buffer, "buffer", 1000, "upload buffer")

	// memcached servers
	flag.StringVar(&options.idfa, "idfa", "127.0.0.1:33013", "ip and port of idfa memcached server")
	flag.StringVar(&options.gaid, "gaid", "127.0.0.1:33014", "ip and port of dvid memcached server")
	flag.StringVar(&options.adid, "adid", "127.0.0.1:33015", "ip and port of dvid memcached server")
	flag.StringVar(&options.dvid, "dvid", "127.0.0.1:33016", "ip and port of dvid memcached server")

	flag.Parse()
	return
}

func dotRename(path string) {
	dir, file := filepath.Split(path)
	err := os.Rename(path, filepath.Join(dir, "."+file))
	if err != nil {
		log.Fatalf("E Can't rename a file: %s", path)
	}
}

// ##############################
// MEMCACHE
// ##############################

func NewMemcache(addr string) *Memcache {
	mc := Memcache{
		address:    addr,
		connection: memcache.New(addr),
	}
	mc.connection.Timeout = MemcacheTimeout
	return &mc
}

// Create MemcacheItem struct from AppsInstalled struct
func NewMemcacheItem(appsInstalled *AppsInstalled) *MemcacheItem {
	ua := &appsinstalled.UserApps{
		Lat:  proto.Float64(appsInstalled.lat),
		Lon:  proto.Float64(appsInstalled.lon),
		Apps: appsInstalled.apps,
	}
	key := fmt.Sprintf("%s:%s", appsInstalled.devType, appsInstalled.devId)
	packed, err := proto.Marshal(ua)
	if err != nil {
		log.Fatal("E Protobuf marshaling error: ", err)
	}
	return &MemcacheItem{
		key:   key,
		value: packed,
	}
}

// Upload to memcache storage
func (mc *Memcache) setItem(key string, value []byte) error {
	item := memcache.Item{
		Key:   key,
		Value: value,
	}

	tries := 3
	delay := 500
	backoff := 2
	if err := mc.connection.Set(&item); err != nil {
		for {
			time.Sleep(time.Duration(delay) * time.Millisecond)
			if err != nil && tries > 0 {
				err = mc.connection.Set(&item)
				tries--
				delay *= backoff
			} else {
				return err
			}
		}
	}
	return nil
}

// Worker for upload data to memcache storage
func MemcacheWorker(memcConn *Memcache, uploadQueue chan *MemcacheItem,
	mcResultQueue chan *Statistic, exit chan bool, dryRun bool) {
	stat := &Statistic{
		processed: 0,
		errors:    0,
	}
	readyLines := 0
	for {
		select {
		case item := <-uploadQueue:
			if dryRun {
				readyLines += 1
				if readyLines%100000 == 0 {
					log.Printf("I %v: ready %v lines", memcConn.address, readyLines)
				}
				stat.processed += 1
				continue
			}

			if err := memcConn.setItem(item.key, item.value); err != nil {
				log.Printf("E Cannot write to memcache %v: %v", memcConn.address, err)
				stat.errors += 1
				continue
			}
			stat.processed += 1
		case <-exit:
			mcResultQueue <- stat
		}
	}
}

// ##############################
// PROCESSING FILES
// ##############################

// Parse line from file to AppsInstalled struct
// Return error if can't parse line
func parseAppsInstalled(line string) (*AppsInstalled, error) {
	lineParts := strings.Split(strings.TrimSpace(line), "\t")
	if len(lineParts) != 5 {
		return nil, errors.New("Quantity of args in line is not valid.")
	}

	devType := strings.TrimSpace(lineParts[0])
	devId := strings.TrimSpace(lineParts[1])
	if devType == "" || devId == "" {
		return nil, errors.New("Device Type or Device Id is not defined.")
	}

	lat, err := strconv.ParseFloat(lineParts[2], 64)
	if err != nil {
		return nil, err
	}

	lon, err := strconv.ParseFloat(lineParts[3], 64)
	if err != nil {
		return nil, err
	}

	rawApps := strings.Split(lineParts[4], ",")
	apps := make([]uint32, 0)
	for _, appStr := range rawApps {
		app, err := strconv.Atoi(appStr)
		if err != nil {
			continue
		}
		apps = append(apps, uint32(app))
	}

	return &AppsInstalled{
		devType: devType,
		devId:   devId,
		lat:     lat,
		lon:     lon,
		apps:    apps,
	}, nil
}

// Read file line by line
// Parse each line to AppsInstalled struct and send it to MemcacheWorkers
// Return statistics of processed file
func processFile(memcPool map[string]*Memcache, fname string, bufferSize int, dryRun bool) *Statistic {
	log.Println("Processing:", fname)

	// Open file
	file, err := os.Open(fname)
	if err != nil {
		log.Fatal("E Cannot open file: ", err)
	}
	defer file.Close()

	// Init GZip reader
	gz, err := gzip.NewReader(file)
	if err != nil {
		log.Fatal("E Cannot create a new GZip Reader: ", err)
	}
	defer gz.Close()

	stat := &Statistic{
		file:      fname,
		processed: 0,
		errors:    0,
	}

	// MemcacheWorker sentinel
	mcWorkerExit := make(chan bool)

	// Run MemcacheWorkers
	mcResultQueue := make(chan *Statistic, len(memcPool))
	uploadQueues := make(map[string]chan *MemcacheItem)
	for devType, memcConn := range memcPool {
		uploadQueues[devType] = make(chan *MemcacheItem, bufferSize)
		go MemcacheWorker(memcConn, uploadQueues[devType], mcResultQueue, mcWorkerExit, dryRun)
	}

	// Processing file line by line
	scanner := bufio.NewScanner(gz)
	for scanner.Scan() {
		line := scanner.Text()
		line = strings.TrimSpace(line)

		if line == "" {
			continue
		}

		appsInstalled, err := parseAppsInstalled(line)
		if err != nil {
			stat.errors += 1
			continue
		}

		queue, ok := uploadQueues[appsInstalled.devType]
		if !ok {
			stat.errors += 1
			log.Println("W Unknow device type:", appsInstalled.devType)
			continue
		}

		// Send data for upload to memcache
		queue <- NewMemcacheItem(appsInstalled)
	}

	// Terminate MemcacheWorkers
	close(mcWorkerExit)

	// Calculate result statistics
	for i := 0; i < len(uploadQueues); i++ {
		result := <-mcResultQueue
		stat.processed += result.processed
		stat.errors += result.errors
	}
	return stat
}

// Worker for processing files
func worker(memcPool map[string]*Memcache, fileQueue chan string,
	resultQueue chan *Statistic, exit chan bool, buffer int, dryRun bool) {
	for {
		select {
		case file := <-fileQueue:
			resultQueue <- processFile(memcPool, file, buffer, dryRun)
		case <-exit:
			return
		}
	}
}

func main() {
	options := parseArgs()
	log.Printf("I Memc loader started with options: %+v", options)

	// Init Logging
	if options.log {
		file, err := os.OpenFile(options.logPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
		if err != nil {
			log.Fatalln("E Failed to open log file", options.logPath, ":", err)
		}
		defer file.Close()

		log.SetOutput(file)
	}

	// Search files
	files, err := filepath.Glob(options.pattern)
	if err != nil {
		// ErrBadPattern
		log.Fatalln("E Used bad pattern:", err)
	}
	if files == nil {
		log.Printf("I Could not find files for the given pattern: %s", options.pattern)
		os.Exit(0)
	}

	// Init connections to Memcache
	memcPool := map[string]*Memcache{
		"idfa": NewMemcache(options.idfa),
		"gaid": NewMemcache(options.gaid),
		"adid": NewMemcache(options.adid),
		"dvid": NewMemcache(options.dvid),
	}

	// Create queue of files
	fileQueue := make(chan string, len(files))
	for _, file := range files {
		fileQueue <- file
	}

	// Create queue of results
	resultQueue := make(chan *Statistic, len(files))

	// Worker sentinel
	workerExit := make(chan bool)
	defer close(workerExit)

	// Start workers
	for i := 0; i < options.workers; i++ {
		go func() {
			worker(memcPool, fileQueue, resultQueue, workerExit, options.buffer, options.dryRun)
		}()
	}

	// Get statistic of processing files
	for i := 0; i < len(files); i++ {
		result := <-resultQueue
		dotRename(result.file)
		log.Printf("I Processing of file %s complete.", result.file)
		if result.processed > 0 {
			errRate := float32(result.errors) / float32(result.processed)
			if errRate < NormalErrRate {
				log.Printf("I Acceptable error rate (%g). Successfull load", errRate)
			} else {
				log.Printf("E High error rate (%g > %g). Failed load", errRate, NormalErrRate)
			}
		}
	}
}
