provider "libvirt" {
  alias = "test"
  uri   = "qemu+ssh://root@perchost.bjd2385.com/system"
  #uri = "qemu:///system"
}

resource "libvirt_pool" "Terra" {
  name = "Terra"
  type = "dir"
  path = "/home/brandon/terra"
}

# resource :: Resource -> Str (local name, referenced within the module)
resource "libvirt_volume" "raw_root" {
  name = "root"
  #pool = libvirt_pool.Terra.name

  # Must be in bites :P
  #size = 10737418240

  # ISO is mounted over NFS, hosted on my primary host.
  source = "root@perchost.bjd2385.com:/home/brandon/terra/images/ubuntu_16/root.raw"
  format = "raw"
}

resource "libvirt_domain" "example" {
  name       = "example"
  memory     = "1024"
  vcpu       = 1
  arch       = "cpu64-rhel6"
  qemu_agent = true

  network_interface {
    bridge   = "br0"
    hostname = "example"
  }

  # Get the disk we created earlier.
  disk {
    volume_id = libvirt_volume.raw_root.id
  }

  console {
    type        = "pty"
    target_type = "serial"
    target_port = "0"
  }

  graphics {
    type        = "spice"
    listen_type = "address"
    autoport    = true
  }
}
