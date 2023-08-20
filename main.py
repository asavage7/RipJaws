import sys, os
import gi
import discid
import musicbrainzngs
import threading
import cdio, pycdio
import music_tag
from PIL import Image
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio

musicbrainzngs.set_useragent("RipJaws", "0.1", "alex.savage07@gmail.com")

class MainApp(Adw.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connect("activate",self.on_activate)

    def on_activate(self, app):
        # Create a Builder
        global builder
        global tracks
        builder = Gtk.Builder()
        builder.add_from_file("window.ui")
        builder.add_from_file("tracklisting.ui")
        builder.add_from_file("aboutwindow.ui")
        builder.add_from_file("preferenceswindow.ui")

        tracks = False

        self.musiclibrarypath = "/home/alex/Music"
        self.musicformat = "mp3"

        self.list_of_tracks = builder.get_object("TrackListing")
        self.album_title = builder.get_object("AlbumTitle")
        self.artist_name = builder.get_object("ArtistName")
        self.release_year = builder.get_object("ReleaseYear")
        self.genre_name = builder.get_object("Genre")
        self.trackCounter = builder.get_object("NumTracks")


        RefreshButton = builder.get_object("RefreshButton")
        RefreshButton.connect("clicked",self.refresh_clicked)

        RipAll = builder.get_object("RipAll")
        RipAll.connect("clicked",self.rip_all_clicked)

        self.status_text = builder.get_object("WindowTitle")
        self.spinner = builder.get_object("ActionBarSpinner")

        try:
            d = cdio.Device(driver_id=pycdio.DRIVER_UNKNOWN)
            cddrive = d.get_device()
        except:
            print("No CD drive connected")

        # Create an action to run a *show about dialog* function we will create 
        show_about_menu = Gio.SimpleAction.new("show_about", None)
        show_about_menu.connect("activate", self.show_about)
        self.add_action(show_about_menu)

        show_preferences= Gio.SimpleAction.new("show_preferences", None)
        show_preferences.connect("activate", self.show_preferences)
        self.add_action(show_preferences)

        self.win = builder.get_object("main_window")
        self.win.set_application(self)  # Application will close once it no longer has active windows attached to it
        self.win.set_title("RipJaws")
        self.win.present()

    def set_status(self, message=str, spin=bool):
        
        #self.spinner.set_spinning(spin)
        self.status_text.set_subtitle(message)
        print(message)

    def rip_all(self):
        opts = " -el "
        global tracks
        self.set_status("Reading disc...", True)
        try:
            d = cdio.Device(driver_id=pycdio.DRIVER_UNKNOWN)
            drive_name = d.get_device()
        except:
            self.set_status("Could not find a disc.", False)
        else:
            if not os.path.exists(self.musiclibrarypath + "/" + self.artist + "/" + self.title):
                os.makedirs(self.musiclibrarypath + "/" + self.artist + "/" + self.title)
            os.chdir(self.musiclibrarypath + "/" + self.artist + "/" + self.title)
            rippath = self.musiclibrarypath + "/" + self.artist + "/" + self.title

            for track in range(d.get_num_tracks()):
                print(self.list_of_tracks.get_row_at_index(track).get_child())
                break
                songpath = rippath + "/{:02d}".format((track + 1)) + " - " + tracks[track]["recording"]["title"]
                self.set_status("Ripping " + tracks[track]["recording"]["title"] + " to " + rippath, True)
                os.system("cdparanoia " + str(track + 1) + ": " + "\"{:02d}".format((track + 1)) + " - " + tracks[track]["recording"]["title"] + ".wav\"")
                self.set_status("Encoding " + tracks[track]["recording"]["title"] + " to " + self.musicformat.upper(), True)
                os.system("ffmpeg -i \"{:02d}".format((track + 1)) + " - " + tracks[track]["recording"]["title"] + ".wav\"" + " -y -ab 320k " + "\"" + rippath + "/{:02d}".format((track + 1)) + " - " + tracks[track]["recording"]["title"] + "." + self.musicformat + "\"")
                os.remove(songpath + ".wav")
                musicfile = music_tag.load_file(rippath + "/{:02d}".format((track + 1)) + " - " + tracks[track]["recording"]["title"] + "." + self.musicformat)
            
                musicfile["title"] = tracks[track]["recording"]["title"]
                musicfile["artist"] = self.artist
                musicfile["album"] = self.title
                musicfile["tracknumber"] = (track + 1)
                try:
                    musicfile["genre"] = self.genre
                except:
                    pass
                musicfile["year"] = self.year

                with open(self.albumartpath, "rb") as albumart:
                    musicfile["artwork"] = albumart.read()
                    albumart.close()

                musicfile.save()
            
            self.set_status("All tracks successfully ripped to", False)
        

    def clear_metadata(self):
            global tracks
            if tracks:
                for track in range(len(tracks)):
                    self.list_of_tracks.remove(self.list_of_tracks.get_row_at_index(0))
                tracks = 0

            self.album_title.set_text("")
            self.artist_name.set_text("")
            self.release_year.set_text("")  
            self.genre_name.set_text("")
            self.trackCounter.set_label("No Disc Inserted")

    def refresh_metadata(self):
        global tracks
        global builder
        self.clear_metadata()

        try:
            d = cdio.Device(driver_id=pycdio.DRIVER_UNKNOWN)
            drive_name = d.get_device()
        except:
            print("Could not find a CD.")

        else:
            try:
                self.set_status("Attempting to get Disc ID... (This may take a while)", True)
                disc = discid.read()
                try:
                    result = musicbrainzngs.get_releases_by_discid(disc.id, includes=["artists","recordings"])
                except musicbrainzngs.ResponseError:
                    self.set_status("Error reading disc or fetching metadata", False)
                else:
                    if result.get("disc"):
                        discRelease = result["disc"]["release-list"][0]
                        self.artist = discRelease["artist-credit-phrase"]
                        self.title = discRelease["title"]
                        self.year = discRelease["date"][0:4]
                        try:
                            self.genre = discRelease["genre"]
                        except:
                            pass
                        tracks = discRelease["medium-list"][0]["track-list"]
                        mbzid = discRelease["id"]
                        self.set_status("Found data For CD " + self.title, True)
                    elif result.get("cdstub"):
                        self.artist = result["cdstub"]["artist"]
                        self.title = result["cdstub"]["title"]
                        self.year = result["cdstub"]["date"][0:4]
                    
                    if not os.path.exists("/tmp/RipJaws"):
                        self.set_status("Creating temp directory", True)
                        os.makedirs("/tmp/RipJaws/")

                    self.albumartpath = str("/tmp/RipJaws/"+mbzid+".jpg")
                    resizedalbumartpath = str("/tmp/RipJaws/"+mbzid+"_small.jpg")
                    
                    self.trackCounter.set_label(("Songs on Disc (" + str(d.get_num_tracks()) + ")"))

                    self.set_status("Adding album data", True)
                    
                    self.album_title.set_text(self.title)
                    self.artist_name.set_text(self.artist)
                    self.release_year.set_text(self.year)
                    try:
                        self.genre_name.set_text(self.genre)
                    except:
                        pass

                    self.set_status("Adding track data", True)

                    for track in range(d.get_num_tracks()):

                        # SingleTrack = Adw.ActionRow.new()

                        # TrackCheckbox = Gtk.CheckButton.new()
                        # TrackCheckbox.set_margin_top(8)
                        # TrackCheckbox.set_margin_bottom(8)

                        # TrackNumberBox = Gtk.CenterBox.new()
                        # TrackNumberBox.set_size_request(32,32)

                        # TrackNumber = Gtk.Label.new()
                        # TrackNumber.set_label(str(track + 1) + ".")
                        # TrackNumber.set_margin_start(8)
                        # TrackNumber.set_justify(Gtk.Justification.RIGHT)

                        # TrackNumberBox.set_center_widget(TrackNumber)

                        # SingleTrack.add_prefix(TrackNumberBox)
                        # SingleTrack.add_prefix(TrackCheckbox)
                        # SingleTrack.set_title(tracks[track]["recording"]["title"])
                        # SingleTrack_subtitle = artist + " - " + title
                        # SingleTrack.set_subtitle(SingleTrack_subtitle)

                        # self.list_of_tracks.append(SingleTrack)

                        TrackRow = Gtk.Builder.new_from_file("tracklisting.ui")
                        SingleTrack = TrackRow.get_object("Track")
                        try:
                            SingleTrack.set_title(tracks[track]["recording"]["title"])
                        except:
                            SingleTrack.set_title("Track " + str(track + 1))
                        SingleTrack.set_subtitle(self.artist + " - " + self.title)
                        TrackNumber = TrackRow.get_object("SongNumber")
                        TrackNumber.set_label(str(track + 1) + ".")
                        self.list_of_tracks.append(SingleTrack)
                        



                    if not os.path.exists(self.albumartpath):
                        self.set_status("Downloading and resizing album art", True)
                        albumart = open(self.albumartpath, "wb")
                        image = musicbrainzngs.get_image_front(mbzid, 512)
                        albumart.write(image)
                        albumart.close()
                        albumart = Image.open(self.albumartpath)
                        resizedalbumart = albumart.resize((160,160))
                        resizedalbumart.save(resizedalbumartpath,quality=90)

                    albumArt = builder.get_object("AlbumArt")
                    albumArt.set_from_file(resizedalbumartpath)

                    self.set_status("CD found and MusicBrainz data added successfully", False)
    


            except Exception as e:
                print(e)
                if discid.disc.DiscError:
                    self.set_status("Error reading disc. Is a CD inserted?", False)
                else:

                        for track in range(d.get_num_tracks()):
                            SingleTrack = Adw.ActionRow.new()
                            SingleTrack.set_title("Track " + str(track + 1))
                            self.list_of_tracks.append(SingleTrack)

                        albumArt = builder.get_object("AlbumArt")
                        albumArt.set_from_file("./no-disc.jpg")

                        self.set_status("An error occoured. Is a CD inserted?", False)
                        self.trackCounter.set_label("No Disc Inserted")

                        self.album_title.set_text("")
                        self.artist_name.set_text("")
                        self.release_year.set_text("")            
        
    def refresh_clicked(self, button):
        self.refreshthread = threading.Thread(target=self.refresh_metadata)
        self.refreshthread.daemon = True
        self.refreshthread.start()

    def rip_all_clicked(self, button):
        self.refreshthread = threading.Thread(target=self.rip_all)
        self.refreshthread.daemon = True
        self.refreshthread.start()

    def show_about(self, show_about_menu, param):
        about_dialog = builder.get_object("AboutRipJaws")
        about_dialog.set_transient_for(app.get_active_window())
        about_dialog.set_visible(True)

    def show_preferences(self, show_about_menu, param):
        preferences_window = builder.get_object("RipJawsSettings")
        preferences_window.set_transient_for(app.get_active_window())
        preferences_window.set_visible(True)

app = MainApp(application_id="com.github.asavage7.ripjaws")
app.run(sys.argv)
