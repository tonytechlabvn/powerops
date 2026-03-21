resource "aws_instance" "broken" {
  ami           = "ami-0c02fb55956c7d316"
  instance_type = "t3.micro"
  # Missing closing brace — intentionally invalid syntax
