resource "aws_nonexistent" "bad" {
  some_attribute = "value"
}

resource "aws_instance" "ok" {
  ami           = "ami-0c02fb55956c7d316"
  instance_type = "t3.micro"
}
